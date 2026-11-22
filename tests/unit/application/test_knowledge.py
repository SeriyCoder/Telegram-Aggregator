import pytest

from telegram_knowledge_base.application.knowledge import (
    create_filter_rule,
    create_tag,
    create_tag_rule,
    query_posts,
    set_bookmark,
    set_manual_tag,
)
from telegram_knowledge_base.domain.models import (
    FilterRule,
    PostPage,
    PostQuery,
    Tag,
    TagRule,
)


class Store:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def create_tag(self, name: str, key: str, color: str | None) -> Tag:
        self.calls.append(("create_tag", (name, key, color)))
        return Tag(1, name, key, color)

    def create_tag_rule(self, tag_id: int, phrase: str) -> TagRule:
        self.calls.append(("create_tag_rule", (tag_id, phrase)))
        return TagRule(1, tag_id, phrase)

    def create_filter_rule(self, kind: str, phrase: str) -> FilterRule:
        self.calls.append(("create_filter_rule", (kind, phrase)))
        return FilterRule(1, kind, phrase)  # type: ignore[arg-type]

    def set_manual_tag(
        self, source_id: str, message_id: int, tag_id: int, present: bool
    ) -> None:
        self.calls.append(("set_manual_tag", (source_id, message_id, tag_id, present)))

    def set_bookmark(self, source_id: str, message_id: int, present: bool) -> None:
        self.calls.append(("set_bookmark", (source_id, message_id, present)))

    def query_posts(self, query: PostQuery) -> PostPage:
        self.calls.append(("query_posts", (query,)))
        return PostPage([])


def test_create_tag_normalizes_a_private_label_only_at_boundary() -> None:
    store = Store()

    result = create_tag(store, "  Python News  ", "#336699")

    assert result == Tag(1, "Python News", "python news", "#336699")
    assert store.calls == [("create_tag", ("Python News", "python news", "#336699"))]


@pytest.mark.parametrize("name", ["", " ", "\n\t"])
def test_empty_tag_never_reaches_storage(name: str) -> None:
    store = Store()

    with pytest.raises(ValueError):
        create_tag(store, name)

    assert store.calls == []


def test_tag_rule_sends_literal_phrase_without_content_to_errors() -> None:
    store = Store()
    secret_phrase = "private rule phrase"

    rule = create_tag_rule(store, 4, f"  {secret_phrase}  ")

    assert rule.phrase == secret_phrase
    assert store.calls == [("create_tag_rule", (4, secret_phrase))]


def test_invalid_tag_rule_is_refused_without_calling_store() -> None:
    store = Store()

    with pytest.raises(ValueError) as error:
        create_tag_rule(store, 4, "  ")

    assert "  " not in str(error.value)
    assert store.calls == []


def test_filter_rules_accept_only_include_and_exclude() -> None:
    store = Store()
    assert create_filter_rule(store, "include", "Python").kind == "include"
    assert create_filter_rule(store, "exclude", "реклама").kind == "exclude"

    with pytest.raises(ValueError):
        create_filter_rule(store, "allow", "anything")  # type: ignore[arg-type]


def test_manual_tag_and_bookmark_are_idempotent_intent_operations() -> None:
    store = Store()

    set_manual_tag(store, "1001", 2, 7, True)
    set_manual_tag(store, "1001", 2, 7, False)
    set_bookmark(store, "1001", 2, True)
    set_bookmark(store, "1001", 2, False)

    assert store.calls == [
        ("set_manual_tag", ("1001", 2, 7, True)),
        ("set_manual_tag", ("1001", 2, 7, False)),
        ("set_bookmark", ("1001", 2, True)),
        ("set_bookmark", ("1001", 2, False)),
    ]


def test_query_posts_validates_without_loading_telegram_or_changing_content() -> None:
    store = Store()
    query = PostQuery(text="PRIVATE QUERY", tag_keys=(" Python ",), limit=10)

    page = query_posts(store, query)

    assert page.items == []
    assert store.calls[0][0] == "query_posts"
    stored = store.calls[0][1][0]
    assert isinstance(stored, PostQuery)
    assert stored.text == "PRIVATE QUERY"
    assert stored.tag_keys == ("python",)
