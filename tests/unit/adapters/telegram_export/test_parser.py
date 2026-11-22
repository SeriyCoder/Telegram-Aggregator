from pathlib import Path

import pytest

import telegram_knowledge_base.adapters.telegram_export.parser as parser_module
from telegram_knowledge_base.adapters.telegram_export.parser import (
    ExportFormatError,
    parse_export,
)
from telegram_knowledge_base.domain.models import ExportKind

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


def test_discussion_group_selects_only_original_channel_posts() -> None:
    export = parse_export(FIXTURES / "discussion_group.json")

    assert export.kind is ExportKind.DISCUSSION_GROUP
    assert export.source.telegram_id == "700000001"
    assert export.source.title == "Synthetic Discussion Group"
    assert export.source.is_channel is False
    assert export.source.is_public is True
    assert [post.message_id for post in export.posts] == [101, 102]
    assert [post.text for post in export.posts] == [
        "synthetic channel post",
        "synthetic caption attached to a photo",
    ]
    assert export.skipped_messages == 4


def test_discussion_group_keeps_original_post_times_in_utc() -> None:
    export = parse_export(FIXTURES / "discussion_group.json")

    assert [post.published_at for post in export.posts] == [
        "2026-03-01T03:00:00Z",
        "2026-03-01T04:00:00Z",
    ]


def test_private_discussion_group_is_accepted(
    tmp_path: Path,
) -> None:
    original = (FIXTURES / "discussion_group.json").read_text(encoding="utf-8")
    private_export = tmp_path / "private_discussion.json"
    private_export.write_text(
        original.replace('"type": "public_supergroup"', '"type": "private_supergroup"'),
        encoding="utf-8",
    )

    export = parse_export(private_export)

    assert export.kind is ExportKind.DISCUSSION_GROUP
    assert export.source.is_public is False
    assert len(export.posts) == 2


def test_discussion_group_marker_requires_channel_forward_identifier(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalid_discussion.json"
    invalid.write_text(
        '{"name":"Unverified Group","type":"public_supergroup","id":7,'
        '"messages":[{"id":1,"type":"message","date_unixtime":"1767225600",'
        '"saved_from":"Private Participant","from":"Private Participant",'
        '"from_id":"user987654321","text":"private synthetic content",'
        '"text_entities":[{"type":"plain","text":"private synthetic content"}]}]}',
        encoding="utf-8",
    )

    with pytest.raises(ExportFormatError) as error:
        parse_export(invalid)

    assert "private synthetic content" not in str(error.value)
    assert "Private Participant" not in str(error.value)
    assert "987654321" not in str(error.value)


def test_discussion_group_without_selected_posts_is_rejected() -> None:
    with pytest.raises(ExportFormatError):
        parse_export(FIXTURES / "group.json")


def test_discussion_group_result_has_no_participant_fields() -> None:
    export = parse_export(FIXTURES / "discussion_group.json")

    for post in export.posts:
        assert not hasattr(post, "author")
        assert not hasattr(post, "author_id")
        assert not hasattr(post, "reply_to_message_id")
        assert not hasattr(post, "reactions")
    rendered = repr(export)
    assert "Private Synthetic Participant" not in rendered
    assert "user987654321" not in rendered
