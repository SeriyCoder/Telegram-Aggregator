import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from telegram_knowledge_base.domain.models import (
    ChannelExport,
    ExportKind,
    Post,
    Source,
)

MAX_EXPORT_BYTES = 512 * 1024 * 1024
_CHANNEL_TYPES = {"public_channel", "private_channel"}
_DISCUSSION_TYPES = {"public_supergroup", "private_supergroup"}


class ExportFormatError(ValueError):
    pass


def parse_export(path: Path) -> ChannelExport:
    document = _load_document(path)
    source, kind = _source(document)
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ExportFormatError("The export file does not contain a message list.")
    if kind is ExportKind.DISCUSSION_GROUP and not any(
        _is_original_channel_post(message) for message in messages
    ):
        raise ExportFormatError(
            "The group export does not contain verifiable channel posts."
        )
    posts: list[Post] = []
    skipped = 0
    for message in messages:
        if kind is ExportKind.DISCUSSION_GROUP and not _is_original_channel_post(
            message
        ):
            if not isinstance(message, dict) or message.get("type") not in {
                "message",
                "service",
            }:
                raise ExportFormatError(
                    "The export contains an unsupported message type."
                )
            skipped += 1
            continue
        post = _post(message)
        if post is None:
            skipped += 1
        else:
            posts.append(post)
    return ChannelExport(source, posts, skipped, kind)


def _load_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ExportFormatError("The export file does not exist.")
    if path.stat().st_size > MAX_EXPORT_BYTES:
        raise ExportFormatError("The export file exceeds the size limit.")
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except UnicodeDecodeError:
        raise ExportFormatError("The export file is not valid UTF-8.") from None
    except json.JSONDecodeError:
        raise ExportFormatError("The export file is not valid JSON.") from None
    except OSError:
        raise ExportFormatError("The export file could not be read.") from None
    if not isinstance(document, dict):
        raise ExportFormatError("The export file is not a chat export.")
    return document


def _source(document: dict[str, Any]) -> tuple[Source, ExportKind]:
    chat_type = document.get("type")
    if chat_type is None:
        raise ExportFormatError(
            "A full account export cannot be imported; export a single channel."
        )
    if chat_type in _CHANNEL_TYPES:
        kind = ExportKind.CHANNEL
    elif chat_type in _DISCUSSION_TYPES:
        kind = ExportKind.DISCUSSION_GROUP
    else:
        raise ExportFormatError(
            "Only channel and discussion-group exports can be imported."
        )
    identifier = document.get("id")
    if not isinstance(identifier, int) or isinstance(identifier, bool):
        raise ExportFormatError("The export header has an invalid source identifier.")
    if identifier < 1:
        raise ExportFormatError("The export header has an invalid source identifier.")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ExportFormatError("The export header has an invalid source name.")
    return (
        Source(
            str(identifier),
            None,
            name,
            kind is ExportKind.CHANNEL,
            chat_type.startswith("public_"),
        ),
        kind,
    )


def _is_original_channel_post(message: object) -> bool:
    if not isinstance(message, dict) or message.get("type") != "message":
        return False
    saved_from = message.get("saved_from")
    forwarded_from_id = message.get("forwarded_from_id")
    return (
        isinstance(saved_from, str)
        and bool(saved_from.strip())
        and isinstance(forwarded_from_id, str)
        and forwarded_from_id.startswith("channel")
    )


def _post(message: object) -> Post | None:
    if not isinstance(message, dict):
        raise ExportFormatError("The export contains an invalid message entry.")
    kind = message.get("type")
    if kind == "service":
        return None
    if kind != "message":
        raise ExportFormatError("The export contains an unsupported message type.")
    identifier = message.get("id")
    if not isinstance(identifier, int) or isinstance(identifier, bool):
        raise ExportFormatError("The export contains an invalid message identifier.")
    if identifier < 1:
        raise ExportFormatError("The export contains an invalid message identifier.")
    published_at = _published_at(message.get("date_unixtime"))
    text = _text(message)
    if not text:
        return None
    return Post(identifier, text, published_at)


def _published_at(value: object) -> str:
    seconds: int | None = None
    if isinstance(value, str) and value.isdigit():
        seconds = int(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        seconds = value
    if seconds is None or seconds < 1:
        raise ExportFormatError("The export contains an invalid message time.")
    return datetime.fromtimestamp(seconds, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(message: dict[str, Any]) -> str:
    entities = message.get("text_entities")
    if entities is None:
        entities = []
    if not isinstance(entities, list):
        raise ExportFormatError("The export contains an invalid text entity list.")
    parts: list[str] = []
    for entity in entities:
        if not isinstance(entity, dict) or not isinstance(entity.get("text"), str):
            raise ExportFormatError("The export contains an invalid text entity.")
        parts.append(entity["text"])
    if parts:
        return "".join(parts)
    fallback = message.get("text")
    return fallback if isinstance(fallback, str) else ""
