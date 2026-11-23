import pytest

from telegram_knowledge_base.web.forms import (
    parse_post_query,
    validate_csrf,
    validate_origin,
)


def test_search_form_builds_safe_query_from_multiple_values() -> None:
    query = parse_post_query(
        {
            "q": "python sqlite",
            "source": "1001",
            "from": "2026-01-01T00:00:00Z",
            "to": "2026-01-31T23:59:59Z",
            "tags": "python,новости",
            "bookmarked": "on",
            "cursor": "",
        }
    )

    assert query.text == "python sqlite"
    assert query.source_id == "1001"
    assert query.tag_keys == ("python", "новости")
    assert query.bookmarked_only is True
    assert query.cursor is None


def test_empty_form_values_mean_an_unfiltered_feed() -> None:
    query = parse_post_query({})

    assert query.text is None
    assert query.source_id is None
    assert query.tag_keys == ()
    assert query.bookmarked_only is False


def test_datetime_local_values_are_normalized_to_utc() -> None:
    query = parse_post_query(
        {
            "from": "2026-11-09T06:45",
            "to": "2026-11-23T06:45",
        }
    )

    assert query.published_from is not None
    assert query.published_to is not None
    assert query.published_from.endswith("Z")
    assert query.published_to.endswith("Z")


def test_csrf_token_must_be_present_and_exact() -> None:
    validate_csrf("expected", "expected")
    with pytest.raises(ValueError):
        validate_csrf("expected", None)
    with pytest.raises(ValueError):
        validate_csrf("expected", "forged")


@pytest.mark.parametrize(
    "origin", [None, "http://127.0.0.1.evil.invalid", "https://127.0.0.1:8765"]
)
def test_post_origin_must_exactly_match_loopback_origin(origin: str | None) -> None:
    with pytest.raises(ValueError):
        validate_origin(origin, "http://127.0.0.1:8765")


def test_exact_loopback_origin_is_allowed() -> None:
    validate_origin("http://127.0.0.1:8765", "http://127.0.0.1:8765")


def test_opaque_browser_origin_is_allowed_with_separate_csrf_gate() -> None:
    validate_origin("null", "http://127.0.0.1:8765")
    validate_csrf("csrf-token", "csrf-token")
