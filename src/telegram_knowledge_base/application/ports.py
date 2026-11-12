from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol

from telegram_knowledge_base.domain.models import Post, Progress, Source


class FloodWait(Exception):
    def __init__(self, seconds: int) -> None:
        if seconds < 1:
            raise ValueError("Flood-wait duration must be positive.")
        self.seconds = seconds
        super().__init__(seconds)


class RateLimited(Exception):
    pass


class SourceAccessError(Exception):
    pass


class SourceResolver(Protocol):
    async def resolve(self, address: str) -> Source: ...


class SourceStore(Protocol):
    def save_source(self, source: Source) -> None: ...


class History(Protocol):
    async def fetch(
        self, source_id: str, *, after: int | None, before: int | None, limit: int
    ) -> list[Post]: ...


class SyncStore(Protocol):
    def is_enabled(self, source_id: str) -> bool: ...

    def get_progress(self, source_id: str) -> Progress: ...

    def commit_batch(
        self, source_id: str, posts: list[Post], progress: Progress
    ) -> None: ...

    def get_cooldown(self) -> datetime | None: ...

    def set_cooldown(self, until: datetime) -> None: ...

    def account_lock(self) -> AbstractAsyncContextManager[None]: ...
