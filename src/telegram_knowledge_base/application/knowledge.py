from typing import Literal

from telegram_knowledge_base.application.ports import KnowledgeStore
from telegram_knowledge_base.domain.filtering import (
    normalize_phrase,
    normalize_tag_key,
    validate_query,
)
from telegram_knowledge_base.domain.models import (
    FilterRule,
    PostPage,
    PostQuery,
    Tag,
    TagRule,
)


def create_tag(store: KnowledgeStore, name: str, color: str | None = None) -> Tag:
    display_name = normalize_phrase(name)
    key = normalize_tag_key(display_name)
    return store.create_tag(display_name, key, color)


def update_tag(
    store: KnowledgeStore, tag_id: int, name: str, color: str | None = None
) -> Tag:
    _positive(tag_id, "tag")
    display_name = normalize_phrase(name)
    return store.update_tag(
        tag_id, display_name, normalize_tag_key(display_name), color
    )


def delete_tag(store: KnowledgeStore, tag_id: int) -> None:
    _positive(tag_id, "tag")
    store.delete_tag(tag_id)


def create_tag_rule(store: KnowledgeStore, tag_id: int, phrase: str) -> TagRule:
    _positive(tag_id, "tag")
    return store.create_tag_rule(tag_id, normalize_phrase(phrase))


def set_tag_rule_enabled(store: KnowledgeStore, rule_id: int, enabled: bool) -> TagRule:
    _positive(rule_id, "tag rule")
    return store.set_tag_rule_enabled(rule_id, enabled)


def delete_tag_rule(store: KnowledgeStore, rule_id: int) -> None:
    _positive(rule_id, "tag rule")
    store.delete_tag_rule(rule_id)


def create_filter_rule(
    store: KnowledgeStore, kind: Literal["include", "exclude"], phrase: str
) -> FilterRule:
    if kind not in {"include", "exclude"}:
        raise ValueError("The filter type is invalid.")
    return store.create_filter_rule(kind, normalize_phrase(phrase))


def set_filter_rule_enabled(
    store: KnowledgeStore, rule_id: int, enabled: bool
) -> FilterRule:
    _positive(rule_id, "filter rule")
    return store.set_filter_rule_enabled(rule_id, enabled)


def delete_filter_rule(store: KnowledgeStore, rule_id: int) -> None:
    _positive(rule_id, "filter rule")
    store.delete_filter_rule(rule_id)


def set_manual_tag(
    store: KnowledgeStore, source_id: str, message_id: int, tag_id: int, present: bool
) -> None:
    _source_and_message(source_id, message_id)
    _positive(tag_id, "tag")
    store.set_manual_tag(source_id, message_id, tag_id, present)


def set_bookmark(
    store: KnowledgeStore, source_id: str, message_id: int, present: bool
) -> None:
    _source_and_message(source_id, message_id)
    store.set_bookmark(source_id, message_id, present)


def query_posts(store: KnowledgeStore, query: PostQuery) -> PostPage:
    return store.query_posts(validate_query(query))


def _positive(value: int, label: str) -> None:
    if value < 1:
        raise ValueError(f"The {label} identifier is invalid.")


def _source_and_message(source_id: str, message_id: int) -> None:
    if not source_id.strip():
        raise ValueError("The source identifier is invalid.")
    _positive(message_id, "message")
