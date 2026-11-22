import pytest

from telegram_knowledge_base.domain.filtering import (
    normalize_phrase,
    normalize_tag_key,
    parse_search_tokens,
    validate_query,
)
from telegram_knowledge_base.domain.models import PostQuery


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Python   News  ", "python news"),
        ("ЁЛКА", "ёлка"),
        ("Israe\u0301l", "israél"),
        ("  política / local  ", "política / local"),
    ],
)
def test_tag_keys_are_stable_unicode_names(raw: str, expected: str) -> None:
    assert normalize_tag_key(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "\t\r\n"])
def test_empty_tag_name_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_tag_key(raw)


def test_rule_phrase_is_trimmed_and_case_preserving() -> None:
    assert normalize_phrase("  Чистая энергия  ") == "Чистая энергия"


@pytest.mark.parametrize("raw", ["", " ", "\t\r\n"])
def test_empty_literal_phrase_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_phrase(raw)


def test_search_text_becomes_safe_unicode_tokens_without_operators() -> None:
    assert parse_search_tokens('Python "новости" AND now() OR FTS5') == (
        "python",
        "новости",
        "and",
        "now",
        "or",
        "fts5",
    )


@pytest.mark.parametrize("raw", [None, "", " --- !!! "])
def test_empty_or_punctuation_only_search_has_no_tokens(
    raw: str | None,
) -> None:
    assert parse_search_tokens(raw) == ()


def test_query_rejects_invalid_page_size_and_dates() -> None:
    with pytest.raises(ValueError):
        validate_query(PostQuery(limit=0))
    with pytest.raises(ValueError):
        validate_query(PostQuery(limit=501))
    with pytest.raises(ValueError):
        validate_query(
            PostQuery(
                published_from="2026-02-01T00:00:00Z",
                published_to="2026-01-01T00:00:00Z",
            )
        )


def test_query_normalizes_tag_keys_and_preserves_order_without_duplicates() -> None:
    query = validate_query(
        PostQuery(tag_keys=(" Python ", "python", "Политика"), limit=50)
    )

    assert query.tag_keys == ("python", "политика")


def test_query_rejects_a_nonlocal_content_cursor() -> None:
    with pytest.raises(ValueError):
        validate_query(PostQuery(cursor="https://example.invalid/private-post"))
