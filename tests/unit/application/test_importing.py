import pytest

from telegram_knowledge_base.application.importing import (
    SourceDisabledError,
    import_channel_export,
)
from telegram_knowledge_base.domain.models import ChannelExport, Post, Source

CHANNEL = Source("1234567890", None, "Synthetic Channel", True, True)
POSTS = [
    Post(10, "first synthetic post", "2026-01-01T00:00:00Z"),
    Post(13, "second synthetic post", "2026-01-02T00:00:00Z"),
]


class Store:
    def __init__(
        self, enabled: bool | None = None, new_posts: int | None = None
    ) -> None:
        self.enabled = enabled
        self.new_posts = new_posts
        self.saved: list[tuple[Source, list[Post]]] = []

    def source_enabled(self, source_id: str) -> bool | None:
        return self.enabled

    def save_import(self, source: Source, posts: list[Post]) -> int:
        self.saved.append((source, posts))
        return len(posts) if self.new_posts is None else self.new_posts


def test_unknown_channel_is_created_and_all_posts_count_as_new() -> None:
    store = Store(enabled=None)

    report = import_channel_export(store, ChannelExport(CHANNEL, POSTS, 2))

    assert store.saved == [(CHANNEL, POSTS)]
    assert report.channel_title == "Synthetic Channel"
    assert report.new_posts == 2
    assert report.existing_posts == 0
    assert report.skipped_messages == 2


def test_overlapping_import_reports_existing_posts() -> None:
    store = Store(enabled=True, new_posts=1)

    report = import_channel_export(store, ChannelExport(CHANNEL, POSTS, 0))

    assert report.new_posts == 1
    assert report.existing_posts == 1


def test_disabled_source_is_refused_without_writing() -> None:
    store = Store(enabled=False)

    with pytest.raises(SourceDisabledError):
        import_channel_export(store, ChannelExport(CHANNEL, POSTS, 0))

    assert store.saved == []


def test_non_channel_export_is_refused_without_writing() -> None:
    group = Source("555000111", None, "Synthetic Group", False, False)
    store = Store(enabled=None)

    with pytest.raises(ValueError):
        import_channel_export(store, ChannelExport(group, POSTS, 0))

    assert store.saved == []


def test_empty_channel_export_reports_zero_counts() -> None:
    store = Store(enabled=True)

    report = import_channel_export(store, ChannelExport(CHANNEL, [], 0))

    assert store.saved == [(CHANNEL, [])]
    assert report.new_posts == 0
    assert report.existing_posts == 0
    assert report.skipped_messages == 0
