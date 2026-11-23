import secrets
from collections.abc import Mapping
from datetime import UTC, datetime

from telegram_knowledge_base.domain.filtering import validate_query
from telegram_knowledge_base.domain.models import PostQuery


def parse_post_query(values: Mapping[str, str]) -> PostQuery:
    raw_tags = values.get("tags", "")
    return validate_query(
        PostQuery(
            text=values.get("q") or None,
            source_id=values.get("source") or None,
            published_from=_utc_datetime_local(values.get("from")),
            published_to=_utc_datetime_local(values.get("to")),
            tag_keys=tuple(
                part.strip() for part in raw_tags.split(",") if part.strip()
            ),
            bookmarked_only=values.get("bookmarked") == "on",
            limit=50,
            cursor=values.get("cursor") or None,
        )
    )


def validate_csrf(expected: str | None, supplied: str | None) -> None:
    if (
        expected is None
        or supplied is None
        or not secrets.compare_digest(expected, supplied)
    ):
        raise ValueError("The request security token is invalid.")


def validate_origin(origin: str | None, expected_origin: str) -> None:
    if origin is None:
        raise ValueError("The request origin is invalid.")
    if origin == "null":
        return
    if not secrets.compare_digest(origin, expected_origin):
        raise ValueError("The request origin is invalid.")


def _utc_datetime_local(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("The publication timestamp is invalid.") from None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
