from dataclasses import dataclass


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
