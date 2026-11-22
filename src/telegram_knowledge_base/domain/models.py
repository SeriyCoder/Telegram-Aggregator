from dataclasses import dataclass
from enum import StrEnum


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
