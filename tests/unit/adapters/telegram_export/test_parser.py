from pathlib import Path

import pytest

import telegram_knowledge_base.adapters.telegram_export.parser as parser_module
from telegram_knowledge_base.adapters.telegram_export.parser import (
    ExportFormatError,
    parse_export,
)

FIXTURES = Path(__file__).parents[3] / "fixtures" / "exports"


def test_channel_export_yields_source_and_posts_with_utc_times() -> None:
    export = parse_export(FIXTURES / "public_channel.json")

    assert export.source.telegram_id == "1234567890"
    assert export.source.title == "Synthetic Channel"
    assert export.source.is_channel is True
    assert export.source.is_public is True
    assert export.source.username is None
    assert [post.message_id for post in export.posts] == [10, 13]
    assert export.posts[0].published_at == "2026-01-01T00:00:00Z"
    assert export.posts[1].published_at == "2026-01-02T00:00:00Z"


def test_post_text_is_assembled_from_text_entities_in_order() -> None:
    export = parse_export(FIXTURES / "public_channel.json")

    assert export.posts[0].text == (
        "Синтетическая часть один https://example.invalid/page"
    )


def test_plain_text_field_is_used_when_text_entities_are_empty() -> None:
    export = parse_export(FIXTURES / "public_channel.json")

    assert export.posts[1].text == "Plain synthetic post"


def test_service_and_textless_messages_are_skipped_and_counted() -> None:
    export = parse_export(FIXTURES / "public_channel.json")

    assert export.skipped_messages == 2


def test_private_channel_export_is_accepted() -> None:
    export = parse_export(FIXTURES / "private_channel.json")

    assert export.source.telegram_id == "987654321"
    assert export.source.is_public is False
    assert len(export.posts) == 1
    assert export.skipped_messages == 0


def test_channel_export_without_messages_yields_no_posts() -> None:
    export = parse_export(FIXTURES / "empty_channel.json")

    assert export.posts == []
    assert export.skipped_messages == 0


@pytest.mark.parametrize(
    "fixture", ["group.json", "personal_chat.json", "full_account.json"]
)
def test_non_channel_exports_are_rejected_without_leaking_content(
    fixture: str,
) -> None:
    with pytest.raises(ExportFormatError) as error:
        parse_export(FIXTURES / fixture)

    assert "must never be imported" not in str(error.value)


def test_corrupted_file_is_rejected_without_quoting_file_content() -> None:
    with pytest.raises(ExportFormatError) as error:
        parse_export(FIXTURES / "corrupted.json")

    assert "Broken Synthetic Channel" not in str(error.value)


def test_message_with_invalid_identifier_rejects_the_whole_file(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "result.json"
    broken.write_text(
        '{"name": "Bad", "type": "public_channel", "id": 1, "messages": ['
        '{"id": 0, "type": "message", "date_unixtime": "1767225600",'
        ' "text": "x", "text_entities": [{"type": "plain", "text": "x"}]}]}',
        encoding="utf-8",
    )

    with pytest.raises(ExportFormatError):
        parse_export(broken)


def test_file_above_size_limit_is_rejected_before_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(parser_module, "MAX_EXPORT_BYTES", 16)

    with pytest.raises(ExportFormatError):
        parse_export(FIXTURES / "public_channel.json")
