import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from conftest import run_offline

from telegram_knowledge_base.application.ports import FloodWait, RateLimited
from telegram_knowledge_base.application.sync import sync_source
from telegram_knowledge_base.domain.models import Post, Progress


class MemoryStore:
    def __init__(self) -> None:
        self.posts: dict[int, Post] = {}
        self.progress = Progress()
        self.deadline: datetime | None = None
        self.reject_commit = False
        self.reject_cooldown_write = False
        self.unavailable = False
        self.enabled = True
        self.lock = asyncio.Lock()

    def is_enabled(self, source_id: str) -> bool:
        return self.enabled

    def get_progress(self, source_id: str) -> Progress:
        return self.progress

    def commit_batch(
        self, source_id: str, posts: list[Post], progress: Progress
    ) -> None:
        if self.reject_commit:
            raise OSError("storage unavailable")
        for post in posts:
            self.posts.setdefault(post.message_id, post)
        self.progress = progress

    def get_cooldown(self) -> datetime | None:
        if self.unavailable:
            raise OSError("storage unavailable")
        return self.deadline

    def set_cooldown(self, until: datetime) -> None:
        if self.unavailable or self.reject_cooldown_write:
            raise OSError("storage unavailable")
        self.deadline = until

    def account_lock(self) -> asyncio.Lock:
        return self.lock


class FakeHistory:
    def __init__(self, posts: list[Post]) -> None:
        self.posts = posts
        self.calls = 0
        self.flood_wait: int | None = None
        self.inflight = 0
        self.max_inflight = 0

    async def fetch(
        self, source_id: str, *, after: int | None, before: int | None, limit: int
    ) -> list[Post]:
        self.calls += 1
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            await asyncio.sleep(0)
            if self.flood_wait is not None:
                raise FloodWait(self.flood_wait)
            posts = [
                post
                for post in self.posts
                if (after is None or post.message_id > after)
                and (before is None or post.message_id < before)
            ]
            return sorted(
                posts, key=lambda post: post.message_id, reverse=after is None
            )[:limit]
        finally:
            self.inflight -= 1


def post(message_id: int, text: str = "text", *, ephemeral: bool = False) -> Post:
    return Post(message_id, text, "2026-01-01T00:00:00Z", ephemeral)


def run_sync(
    store: MemoryStore,
    history: FakeHistory,
    *,
    limit: int,
    now: datetime,
    source_id: str = "123",
) -> None:
    run_offline(sync_source(store, history, source_id, limit=limit, now=lambda: now))


NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_initial_sync_respects_500_limit_and_starts_with_latest() -> None:
    store = MemoryStore()
    history = FakeHistory([post(i) for i in range(1, 521)])

    run_sync(store, history, limit=500, now=NOW)

    assert len(store.posts) == 500
    assert set(store.posts) == set(range(21, 521))


def test_overdelivering_history_adapter_cannot_exceed_run_limit() -> None:
    class OverdeliveringHistory(FakeHistory):
        async def fetch(
            self,
            source_id: str,
            *,
            after: int | None,
            before: int | None,
            limit: int,
        ) -> list[Post]:
            return [post(i) for i in range(501, 0, -1)]

    store = MemoryStore()
    run_sync(store, OverdeliveringHistory([]), limit=500, now=NOW)

    assert len(store.posts) == 500
    assert set(store.posts) == set(range(2, 502))


def test_backfill_and_new_posts_both_progress_with_single_message_limit() -> None:
    store = MemoryStore()
    history = FakeHistory([post(8), post(9), post(10)])
    run_sync(store, history, limit=1, now=NOW)
    assert set(store.posts) == {10}

    history.posts.append(post(11))
    run_sync(store, history, limit=1, now=NOW)
    run_sync(store, history, limit=1, now=NOW)

    assert set(store.posts) == {9, 10, 11}


def test_repeated_sync_keeps_existing_snapshot_and_skips_ephemeral_content() -> None:
    store = MemoryStore()
    history = FakeHistory([post(1, "original"), post(2, ephemeral=True)])
    run_sync(store, history, limit=10, now=NOW)
    history.posts = [post(1, "edited")]

    run_sync(store, history, limit=10, now=NOW)

    assert store.posts == {1: post(1, "original")}


def test_empty_history_saves_no_posts() -> None:
    store = MemoryStore()
    run_sync(store, FakeHistory([]), limit=1, now=NOW)
    assert store.posts == {}


def test_disabled_source_is_rejected_before_fetch() -> None:
    store = MemoryStore()
    store.enabled = False
    history = FakeHistory([post(1)])

    with pytest.raises(ValueError):
        run_sync(store, history, limit=1, now=NOW)

    assert history.calls == 0


@pytest.mark.parametrize("limit", [0, 501])
def test_out_of_range_limit_fails_before_request(limit: int) -> None:
    store = MemoryStore()
    history = FakeHistory([post(1)])
    with pytest.raises(ValueError):
        run_sync(store, history, limit=limit, now=NOW)
    assert history.calls == 0


def test_failed_batch_does_not_advance_cursor_and_can_be_retried() -> None:
    store = MemoryStore()
    history = FakeHistory([post(1), post(2)])
    store.reject_commit = True

    with pytest.raises(OSError):
        run_sync(store, history, limit=2, now=NOW)
    assert store.posts == {}
    assert store.progress == Progress()

    store.reject_commit = False
    run_sync(store, history, limit=2, now=NOW)
    assert set(store.posts) == {1, 2}


def test_flood_wait_survives_restart_and_forbids_early_requests() -> None:
    store = MemoryStore()
    history = FakeHistory([post(1)])
    history.flood_wait = 60
    with pytest.raises(RateLimited):
        run_sync(store, history, limit=1, now=NOW)
    assert store.deadline == NOW + timedelta(seconds=60)
    assert history.calls == 1

    history.flood_wait = None
    with pytest.raises(RateLimited):
        run_sync(
            store, history, limit=1, now=NOW + timedelta(seconds=59), source_id="456"
        )
    assert history.calls == 1

    run_sync(store, history, limit=1, now=NOW + timedelta(seconds=60))
    assert history.calls > 1
    assert set(store.posts) == {1}


def test_failure_to_persist_flood_wait_does_not_retry() -> None:
    store = MemoryStore()
    store.reject_cooldown_write = True
    history = FakeHistory([post(1)])
    history.flood_wait = 60

    with pytest.raises(OSError):
        run_sync(store, history, limit=1, now=NOW)

    assert history.calls == 1
    assert store.posts == {}


def test_unavailable_cooldown_storage_prevents_network_requests() -> None:
    store = MemoryStore()
    store.unavailable = True
    history = FakeHistory([post(1)])

    with pytest.raises(OSError):
        run_sync(store, history, limit=1, now=NOW)

    assert history.calls == 0


def test_parallel_syncs_do_not_issue_parallel_requests() -> None:
    async def exercise() -> None:
        store = MemoryStore()
        history = FakeHistory([post(1), post(2)])
        await asyncio.gather(
            sync_source(store, history, "123", limit=1, now=lambda: NOW),
            sync_source(store, history, "123", limit=1, now=lambda: NOW),
        )
        assert history.max_inflight == 1

    run_offline(exercise())
