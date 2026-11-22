import base64
import re
import unicodedata
from datetime import datetime

from telegram_knowledge_base.domain.models import PostQuery


def normalize_tag_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).casefold()
    key = " ".join(normalized.split())
    if not key:
        raise ValueError("A tag name is required.")
    return key


def normalize_phrase(phrase: str) -> str:
    normalized = unicodedata.normalize("NFKC", phrase).strip()
    if not normalized:
        raise ValueError("A literal phrase is required.")
    return normalized


def parse_search_tokens(text: str | None) -> tuple[str, ...]:
    if text is None:
        return ()
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def validate_query(query: PostQuery) -> PostQuery:
    if not 1 <= query.limit <= 500:
        raise ValueError("The page size must be between 1 and 500.")
    source_id = query.source_id
    if source_id is not None and not source_id.strip():
        raise ValueError("The source identifier is invalid.")
    if query.published_from is not None:
        _timestamp(query.published_from)
    if query.published_to is not None:
        _timestamp(query.published_to)
    if (
        query.published_from is not None
        and query.published_to is not None
        and query.published_from > query.published_to
    ):
        raise ValueError("The publication range is invalid.")
    tag_keys: list[str] = []
    for raw_key in query.tag_keys:
        key = normalize_tag_key(raw_key)
        if key not in tag_keys:
            tag_keys.append(key)
    decode_cursor(query.cursor)
    return PostQuery(
        text=query.text,
        source_id=source_id,
        published_from=query.published_from,
        published_to=query.published_to,
        tag_keys=tuple(tag_keys),
        bookmarked_only=query.bookmarked_only,
        limit=query.limit,
        cursor=query.cursor,
    )


def encode_cursor(offset: int) -> str:
    if offset < 0:
        raise ValueError("The pagination offset must not be negative.")
    encoded = base64.urlsafe_b64encode(str(offset).encode("ascii"))
    return encoded.decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(cursor + padding).decode("ascii")
        if not decoded.isdigit():
            raise ValueError
        return int(decoded)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("The pagination cursor is invalid.") from None


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("The publication timestamp is invalid.") from None
    if parsed.tzinfo is None:
        raise ValueError("The publication timestamp must include a timezone.")
    return parsed
