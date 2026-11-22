from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


@dataclass(frozen=True, slots=True)
class Source:
    telegram_id: str
    username: str | None
    title: str
    is_channel: bool
    is_public: bool
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Post:
    message_id: int
    text: str
    published_at: str
    ephemeral: bool = False


@dataclass(frozen=True, slots=True)
class Progress:
    newest_id: int | None = None
    oldest_id: int | None = None
    backfill_complete: bool = False
    next_direction: str = "older"


class ExportKind(StrEnum):
    CHANNEL = "channel"
    DISCUSSION_GROUP = "discussion_group"


@dataclass(frozen=True, slots=True)
class ChannelExport:
    source: Source
    posts: list[Post]
    skipped_messages: int
    kind: ExportKind = ExportKind.CHANNEL


@dataclass(frozen=True, slots=True)
class ImportReport:
    channel_title: str
    new_posts: int
    existing_posts: int
    skipped_messages: int

    @property
    def source_title(self) -> str:
        return self.channel_title


@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
    key: str
    color: str | None = None


@dataclass(frozen=True, slots=True)
class TagRule:
    id: int
    tag_id: int
    phrase: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class FilterRule:
    id: int
    kind: Literal["include", "exclude"]
    phrase: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PostQuery:
    text: str | None = None
    source_id: str | None = None
    published_from: str | None = None
    published_to: str | None = None
    tag_keys: tuple[str, ...] = ()
    bookmarked_only: bool = False
    limit: int = 50
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class PostRecord:
    source_id: str
    source_title: str
    post: Post
    tags: tuple[Tag, ...] = ()
    manual_tag_ids: frozenset[int] = frozenset()
    bookmarked: bool = False


@dataclass(frozen=True, slots=True)
class PostPage:
    items: list[PostRecord]
    next_cursor: str | None = None
