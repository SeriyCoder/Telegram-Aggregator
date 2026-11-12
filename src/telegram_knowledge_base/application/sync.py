import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta

from telegram_knowledge_base.application.ports import (
    FloodWait,
    History,
    RateLimited,
    SyncStore,
)
from telegram_knowledge_base.domain.models import Post, Progress


def _advance(progress: Progress, posts: list[Post]) -> Progress:
    if not posts:
        return progress
    ids = [post.message_id for post in posts]
    return Progress(
        newest_id=max(progress.newest_id or max(ids), max(ids)),
        oldest_id=min(progress.oldest_id or min(ids), min(ids)),
        backfill_complete=progress.backfill_complete,
        next_direction=progress.next_direction,
    )


async def _fetch(
    history: History,
    source_id: str,
    *,
    after: int | None,
    before: int | None,
    limit: int,
) -> list[Post]:
    if limit <= 0:
        return []
    posts = await history.fetch(source_id, after=after, before=before, limit=limit)
    return posts[:limit]


async def sync_source(
    store: SyncStore,
    history: History,
    source_id: str,
    *,
    limit: int,
    now: Callable[[], datetime],
) -> None:
    if not 1 <= limit <= 500:
        raise ValueError("Collection limit must be between 1 and 500.")

    async with store.account_lock():
        started = now()
        if started.tzinfo is None:
            raise ValueError("Synchronization clock must return a timezone-aware time.")
        enabled = await asyncio.to_thread(store.is_enabled, source_id)
        if not enabled:
            raise ValueError("The selected source is unavailable or disabled.")
        cooldown = await asyncio.to_thread(store.get_cooldown)
        if cooldown is not None and cooldown > started:
            raise RateLimited("Telegram requested a waiting period.")

        progress = await asyncio.to_thread(store.get_progress, source_id)
        if progress.next_direction not in {"older", "newer"}:
            raise ValueError("Invalid synchronization direction.")
        collected: list[Post] = []
        raw: list[Post] = []

        try:
            if progress.newest_id is None and progress.oldest_id is None:
                raw = await _fetch(
                    history,
                    source_id,
                    after=None,
                    before=None,
                    limit=limit,
                )
                collected.extend(raw)
                progress = _advance(progress, raw)
                progress = Progress(
                    newest_id=progress.newest_id,
                    oldest_id=progress.oldest_id,
                    backfill_complete=len(raw) < limit,
                    next_direction="older",
                )
            elif progress.backfill_complete:
                raw = await _fetch(
                    history,
                    source_id,
                    after=progress.newest_id,
                    before=None,
                    limit=limit,
                )
                collected.extend(raw)
                progress = _advance(progress, raw)
            else:
                first_direction = progress.next_direction
                first_quota = (limit + 1) // 2
                if limit == 1:
                    first_quota = 1

                if first_direction == "older":
                    first = await _fetch(
                        history,
                        source_id,
                        after=None,
                        before=progress.oldest_id,
                        limit=first_quota,
                    )
                    collected.extend(first)
                    progress = _advance(progress, first)
                    if len(first) < first_quota:
                        progress = Progress(
                            progress.newest_id,
                            progress.oldest_id,
                            True,
                            "newer",
                        )
                    remaining = limit - len(first)
                    if remaining:
                        second = await _fetch(
                            history,
                            source_id,
                            after=progress.newest_id,
                            before=None,
                            limit=remaining,
                        )
                        collected.extend(second)
                        progress = _advance(progress, second)
                    next_direction = "newer"
                else:
                    first = await _fetch(
                        history,
                        source_id,
                        after=progress.newest_id,
                        before=None,
                        limit=first_quota,
                    )
                    collected.extend(first)
                    progress = _advance(progress, first)
                    remaining = limit - len(first)
                    if remaining:
                        second = await _fetch(
                            history,
                            source_id,
                            after=None,
                            before=progress.oldest_id,
                            limit=remaining,
                        )
                        collected.extend(second)
                        progress = _advance(progress, second)
                        if len(second) < remaining:
                            progress = Progress(
                                progress.newest_id,
                                progress.oldest_id,
                                True,
                                "older",
                            )
                    next_direction = "older"
                progress = Progress(
                    progress.newest_id,
                    progress.oldest_id,
                    progress.backfill_complete,
                    next_direction,
                )
        except FloodWait as error:
            await asyncio.to_thread(
                store.set_cooldown, started + timedelta(seconds=error.seconds)
            )
            raise RateLimited("Telegram requested a waiting period.") from None

        if raw and not progress.backfill_complete and len(raw) < limit:
            progress = Progress(
                progress.newest_id,
                progress.oldest_id,
                True,
                progress.next_direction,
            )
        await asyncio.to_thread(
            store.commit_batch,
            source_id,
            [post for post in collected if not post.ephemeral],
            progress,
        )
