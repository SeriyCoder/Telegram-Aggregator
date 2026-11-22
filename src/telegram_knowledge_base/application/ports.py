from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol

from telegram_knowledge_base.domain.models import (
    FilterRule,
    Post,
    PostPage,
    PostQuery,
    Progress,
    Source,
    Tag,
    TagRule,
)


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


class ImportStore(Protocol):
    def source_enabled(self, source_id: str) -> bool | None: ...

    def save_import(self, source: Source, posts: list[Post]) -> int: ...


class KnowledgeStore(Protocol):
    def create_tag(self, name: str, key: str, color: str | None) -> Tag: ...

    def update_tag(
        self, tag_id: int, name: str, key: str, color: str | None
    ) -> Tag: ...

    def delete_tag(self, tag_id: int) -> None: ...

    def create_tag_rule(self, tag_id: int, phrase: str) -> TagRule: ...

    def set_tag_rule_enabled(self, rule_id: int, enabled: bool) -> TagRule: ...

    def delete_tag_rule(self, rule_id: int) -> None: ...

    def create_filter_rule(self, kind: str, phrase: str) -> FilterRule: ...

    def set_filter_rule_enabled(self, rule_id: int, enabled: bool) -> FilterRule: ...

    def delete_filter_rule(self, rule_id: int) -> None: ...

    def set_manual_tag(
        self, source_id: str, message_id: int, tag_id: int, present: bool
    ) -> None: ...

    def set_bookmark(self, source_id: str, message_id: int, present: bool) -> None: ...

    def query_posts(self, query: PostQuery) -> PostPage: ...
