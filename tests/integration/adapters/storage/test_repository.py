import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from telegram_knowledge_base.adapters.storage.lock import AccountLock
from telegram_knowledge_base.adapters.storage.repository import Repository
from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
from telegram_knowledge_base.domain.models import Post, PostQuery, Progress, Source


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)
    return Repository(database)


@pytest.fixture
def knowledge_repository(tmp_path: Path) -> Repository:
    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)
    repository = Repository(database)
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "knowledge"
        / "russian_posts.json"
    )
    document = json.loads(fixture.read_text(encoding="utf-8"))
    for item in document["sources"]:
        source = Source(
            item["telegram_id"],
            None,
            item["title"],
            item["is_channel"],
            item["is_public"],
        )
        posts = [
            Post(post["message_id"], post["text"], post["published_at"])
            for post in item["posts"]
        ]
        repository.save_import(source, posts)
    return repository


def test_sources_can_be_enabled_and_disabled(repository: Repository) -> None:
    source = Source("123", "public_channel", "Example", True, True)
    repository.save_source(source)
    repository.set_enabled("123", False)
    assert repository.list_sources() == [
        Source("123", "public_channel", "Example", True, True, False)
    ]
    repository.set_enabled("123", True)
    assert repository.list_sources() == [source]


def test_duplicate_batch_preserves_original_snapshot(repository: Repository) -> None:
    repository.save_source(Source("123", "public_channel", "Example", True, True))
    original = Post(1, "original", "2026-01-01T00:00:00Z")
    progress = Progress(newest_id=1, oldest_id=1)
    repository.commit_batch("123", [original], progress)
    repository.commit_batch(
        "123", [Post(1, "edited", "2026-01-01T00:00:00Z")], progress
    )
    assert repository.list_posts("123") == [original]
    assert repository.get_progress("123") == progress


def test_invalid_batch_rolls_back_both_posts_and_progress(
    repository: Repository,
) -> None:
    repository.save_source(Source("123", "public_channel", "Example", True, True))
    previous = repository.get_progress("123")
    with sqlite3.connect(repository.database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_second BEFORE INSERT ON posts "
            "WHEN NEW.message_id = 2 BEGIN SELECT RAISE(ABORT, 'test failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        repository.commit_batch(
            "123",
            [
                Post(1, "first", "2026-01-01T00:00:00Z"),
                Post(2, "second", "2026-01-01T00:00:00Z"),
            ],
            Progress(newest_id=2, oldest_id=1),
        )
    assert repository.list_posts("123") == []
    assert repository.get_progress("123") == previous


def test_cooldown_is_persisted_across_repository_instances(
    repository: Repository,
) -> None:
    deadline = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=60)
    repository.set_cooldown(deadline)

    assert Repository(repository.database).get_cooldown() == deadline


def test_imported_private_channel_without_username_is_stored(
    repository: Repository,
) -> None:
    source = Source("987654321", None, "Закрытый синтетический канал", True, False)
    posts = [Post(7, "единственная запись", "2026-02-01T00:00:00Z")]

    created = repository.save_import(source, posts)

    assert created == 1
    assert repository.source_enabled("987654321") is True
    assert repository.list_posts("987654321") == posts


def test_repeated_import_creates_no_duplicates_and_keeps_first_version(
    repository: Repository,
) -> None:
    source = Source("1234567890", None, "Synthetic Channel", True, True)
    original = Post(10, "original text", "2026-01-01T00:00:00Z")
    assert repository.save_import(source, [original]) == 1

    created = repository.save_import(
        source,
        [
            Post(10, "edited text", "2026-01-01T00:00:00Z"),
            Post(13, "new post", "2026-01-02T00:00:00Z"),
        ],
    )

    assert created == 1
    assert repository.list_posts("1234567890") == [
        original,
        Post(13, "new post", "2026-01-02T00:00:00Z"),
    ]


def test_import_with_invalid_post_changes_nothing(repository: Repository) -> None:
    source = Source("1234567890", None, "Synthetic Channel", True, True)

    with pytest.raises(ValueError):
        repository.save_import(
            source,
            [
                Post(10, "valid", "2026-01-01T00:00:00Z"),
                Post(0, "invalid identifier", "2026-01-01T00:00:00Z"),
            ],
        )

    assert repository.source_enabled("1234567890") is None
    assert repository.count_posts() == 0


def test_import_does_not_touch_sync_cursors_or_cooldown(
    repository: Repository,
) -> None:
    source = Source("1234567890", None, "Synthetic Channel", True, True)

    repository.save_import(source, [Post(10, "text", "2026-01-01T00:00:00Z")])

    assert repository.get_progress("1234567890") == Progress()
    assert repository.get_cooldown() is None


def test_source_enabled_distinguishes_missing_and_disabled(
    repository: Repository,
) -> None:
    assert repository.source_enabled("1234567890") is None

    repository.save_import(
        Source("1234567890", None, "Synthetic Channel", True, True), []
    )
    repository.set_enabled("1234567890", False)

    assert repository.source_enabled("1234567890") is False


def test_discussion_group_can_store_original_channel_posts(
    repository: Repository,
) -> None:
    discussion = Source("700000001", None, "Synthetic Discussion Group", False, True)
    posts = [
        Post(101, "channel post", "2026-03-01T03:00:00Z"),
        Post(102, "caption", "2026-03-01T04:00:00Z"),
    ]

    assert repository.save_import(discussion, posts) == 2
    assert repository.source_enabled("700000001") is True
    assert repository.list_posts("700000001") == posts


def test_repeated_discussion_import_preserves_the_first_post_version(
    repository: Repository,
) -> None:
    discussion = Source("700000001", None, "Synthetic Discussion Group", False, True)
    original = Post(101, "original post", "2026-03-01T03:00:00Z")
    repository.save_import(discussion, [original])

    assert (
        repository.save_import(
            discussion,
            [
                Post(101, "edited post", "2026-03-01T03:00:00Z"),
                Post(102, "new post", "2026-03-01T04:00:00Z"),
            ],
        )
        == 1
    )
    assert repository.list_posts("700000001") == [
        original,
        Post(102, "new post", "2026-03-01T04:00:00Z"),
    ]


def test_invalid_discussion_import_rolls_back_source_and_posts(
    repository: Repository,
) -> None:
    discussion = Source("700000001", None, "Synthetic Discussion Group", False, True)
    original = Post(101, "original post", "2026-03-01T03:00:00Z")
    assert repository.save_import(discussion, [original]) == 1

    with pytest.raises(ValueError):
        repository.save_import(
            discussion,
            [
                Post(102, "valid post", "2026-03-01T04:00:00Z"),
                Post(0, "invalid", "2026-03-01T05:00:00Z"),
            ],
        )

    assert repository.source_enabled("700000001") is True
    assert repository.list_posts("700000001") == [original]


def test_tags_can_be_created_from_scratch_and_listed(
    knowledge_repository: Repository,
) -> None:
    tag = knowledge_repository.create_tag("Python", "python", "#3572A5")
    second = knowledge_repository.create_tag("Израиль", "израиль", None)

    assert tag.name == "Python"
    assert tag.key == "python"
    assert knowledge_repository.list_tags() == [tag, second]


def test_tag_keys_are_unique_without_text_in_the_error(
    knowledge_repository: Repository,
) -> None:
    secret = "private-python-name"
    knowledge_repository.create_tag(secret, "python", None)

    with pytest.raises(ValueError) as error:
        knowledge_repository.create_tag("Other private name", "python", None)

    assert secret not in str(error.value)
    assert "Other private name" not in str(error.value)


def test_automatic_tags_recompute_for_existing_posts_and_respect_enabled(
    knowledge_repository: Repository,
) -> None:
    tag = knowledge_repository.create_tag("Python", "python", None)
    rule = knowledge_repository.create_tag_rule(tag.id, "python")

    before = knowledge_repository.query_posts(PostQuery(tag_keys=("python",)))
    assert [(record.source_id, record.post.message_id) for record in before.items] == [
        ("1001", 1),
        ("1001", 3),
    ]

    knowledge_repository.set_tag_rule_enabled(rule.id, False)
    after = knowledge_repository.query_posts(PostQuery(tag_keys=("python",)))
    assert after.items == []


def test_manual_tag_survives_disabling_automatic_rule(
    knowledge_repository: Repository,
) -> None:
    tag = knowledge_repository.create_tag("Python", "python", None)
    rule = knowledge_repository.create_tag_rule(tag.id, "python")
    knowledge_repository.set_manual_tag("1001", 1, tag.id, True)
    knowledge_repository.set_tag_rule_enabled(rule.id, False)

    page = knowledge_repository.query_posts(PostQuery(tag_keys=("python",)))

    assert [(item.source_id, item.post.message_id) for item in page.items] == [
        ("1001", 1)
    ]
    assert page.items[0].manual_tag_ids == frozenset({tag.id})


def test_filter_include_rules_are_or_and_exclude_is_applied_after(
    knowledge_repository: Repository,
) -> None:
    knowledge_repository.create_filter_rule("include", "python")
    knowledge_repository.create_filter_rule("include", "Израиль")
    knowledge_repository.create_filter_rule("exclude", "реклама")

    page = knowledge_repository.query_posts(PostQuery())

    assert [(item.source_id, item.post.message_id) for item in page.items] == [
        ("1001", 1),
        ("1001", 2),
        ("1002", 1),
        ("1001", 3),
    ]


def test_disabling_the_only_include_filter_restores_non_excluded_posts(
    knowledge_repository: Repository,
) -> None:
    include = knowledge_repository.create_filter_rule("include", "python")
    knowledge_repository.create_filter_rule("exclude", "реклама")
    knowledge_repository.set_filter_rule_enabled(include.id, False)

    page = knowledge_repository.query_posts(PostQuery())

    assert len(page.items) == 4
    assert all("реклама" not in record.post.text.casefold() for record in page.items)


def test_multiple_selected_tags_are_combined_with_or(
    knowledge_repository: Repository,
) -> None:
    python_tag = knowledge_repository.create_tag("Python", "python", None)
    israel_tag = knowledge_repository.create_tag("Израиль", "израиль", None)
    knowledge_repository.create_tag_rule(python_tag.id, "python")
    knowledge_repository.create_tag_rule(israel_tag.id, "израиль")

    page = knowledge_repository.query_posts(PostQuery(tag_keys=("python", "израиль")))

    assert {(item.source_id, item.post.message_id) for item in page.items} == {
        ("1001", 1),
        ("1001", 2),
        ("1001", 3),
        ("1002", 1),
    }


def test_full_text_search_handles_cyrillic_case_and_and_tokens(
    knowledge_repository: Repository,
) -> None:
    cyrillic = knowledge_repository.query_posts(PostQuery(text="ИЗРАИЛЬ"))
    conjunction = knowledge_repository.query_posts(PostQuery(text="python sqlite"))

    assert len(cyrillic.items) == 2
    assert [(item.source_id, item.post.message_id) for item in conjunction.items] == [
        ("1001", 1)
    ]


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("OR", [("1002", 2)]),
        ("NOW()", [("1001", 4)]),
        ('"python"', [("1001", 1), ("1001", 3)]),
        ("нет совпадений", []),
    ],
)
def test_search_treats_special_input_as_literal_text_not_syntax(
    knowledge_repository: Repository,
    search: str,
    expected: list[tuple[str, int]],
) -> None:
    page = knowledge_repository.query_posts(PostQuery(text=search))

    assert [(item.source_id, item.post.message_id) for item in page.items] == expected


def test_empty_search_query_returns_the_unsearched_filtered_feed(
    knowledge_repository: Repository,
) -> None:
    plain = knowledge_repository.query_posts(PostQuery())
    punctuation = knowledge_repository.query_posts(PostQuery(text=" --- !!! "))

    assert [item.post.message_id for item in plain.items] == [
        item.post.message_id for item in punctuation.items
    ]
    assert len(plain.items) == 6


def test_fts_stays_in_sync_after_insert_update_and_delete(
    knowledge_repository: Repository,
) -> None:
    source = Source("1001", None, "Synthetic Tech", True, True)
    knowledge_repository.save_import(
        source,
        [Post(5, "новый редкий термин", "2026-01-04T10:00:00Z")],
    )
    assert (
        len(knowledge_repository.query_posts(PostQuery(text="редкий термин")).items)
        == 1
    )

    with sqlite3.connect(knowledge_repository.database) as connection:
        connection.execute(
            "UPDATE posts SET text = ? "
            "WHERE source_id = (SELECT id FROM sources WHERE telegram_id = ?) "
            "AND message_id = ?",
            ("заменённый текст", "1001", 5),
        )
        connection.execute(
            "DELETE FROM posts WHERE source_id = "
            "(SELECT id FROM sources WHERE telegram_id = ?) AND message_id = ?",
            ("1001", 1),
        )

    assert knowledge_repository.query_posts(PostQuery(text="редкий")).items == []
    assert (
        knowledge_repository.query_posts(PostQuery(text="заменённый"))
        .items[0]
        .post.message_id
        == 5
    )
    assert knowledge_repository.query_posts(PostQuery(text="sqlite")).items == []


def test_bookmarks_are_idempotent_and_can_filter_the_feed(
    knowledge_repository: Repository,
) -> None:
    knowledge_repository.set_bookmark("1001", 2, True)
    knowledge_repository.set_bookmark("1001", 2, True)
    page = knowledge_repository.query_posts(PostQuery(bookmarked_only=True))

    assert [(item.source_id, item.post.message_id) for item in page.items] == [
        ("1001", 2)
    ]
    assert page.items[0].bookmarked is True

    knowledge_repository.set_bookmark("1001", 2, False)
    knowledge_repository.set_bookmark("1001", 2, False)
    assert knowledge_repository.query_posts(PostQuery(bookmarked_only=True)).items == []


def test_query_combines_source_date_search_tag_and_bookmark(
    knowledge_repository: Repository,
) -> None:
    tag = knowledge_repository.create_tag("Python", "python", None)
    knowledge_repository.create_tag_rule(tag.id, "python")
    knowledge_repository.set_bookmark("1001", 1, True)

    page = knowledge_repository.query_posts(
        PostQuery(
            text="sqlite",
            source_id="1001",
            published_from="2026-01-03T00:00:00Z",
            published_to="2026-01-03T23:59:59Z",
            tag_keys=("python",),
            bookmarked_only=True,
        )
    )

    assert [(item.source_id, item.post.message_id) for item in page.items] == [
        ("1001", 1)
    ]


def test_pagination_is_stable_for_equal_dates_and_has_no_duplicates(
    knowledge_repository: Repository,
) -> None:
    seen: list[tuple[str, int]] = []
    cursor = None

    while True:
        page = knowledge_repository.query_posts(PostQuery(limit=2, cursor=cursor))
        seen.extend((item.source_id, item.post.message_id) for item in page.items)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor

    assert len(seen) == 6
    assert len(set(seen)) == 6
    assert seen[:3] == [("1001", 1), ("1001", 2), ("1002", 1)]


def test_search_results_do_not_expose_commenter_fields_or_file_paths(
    knowledge_repository: Repository,
) -> None:
    page = knowledge_repository.query_posts(PostQuery(text="python"))

    rendered = repr(page)
    assert "user987654321" not in rendered
    assert "Private Synthetic Participant" not in rendered
    assert str(knowledge_repository.database) not in rendered


def test_query_does_not_touch_sync_cursors_or_cooldown(
    knowledge_repository: Repository,
) -> None:
    knowledge_repository.query_posts(PostQuery(text="python"))

    assert knowledge_repository.get_cooldown() is None
    with sqlite3.connect(knowledge_repository.database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sync_state").fetchone() == (0,)


def test_account_lock_excludes_another_process_and_is_released(tmp_path: Path) -> None:
    lock_path = tmp_path / "account.lock"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[4] / "src")
    script = (
        "import sys, socket\n"
        "from pathlib import Path\n"
        "attempts = []\n"
        "def reject(*args, **kwargs):\n"
        "    attempts.append(True)\n"
        "    raise AssertionError('Network is forbidden')\n"
        "for name in ('connect', 'connect_ex', 'bind', 'listen', 'send', "
        "'sendall', 'sendto'):\n"
        "    setattr(socket.socket, name, reject)\n"
        "for name in ('getaddrinfo', 'gethostbyname', 'gethostbyname_ex', "
        "'gethostbyaddr'):\n"
        "    setattr(socket, name, reject)\n"
        "from telegram_knowledge_base.adapters.storage.lock import "
        "AccountInUse, AccountLock\n"
        "status = 0\n"
        "try:\n"
        "    with AccountLock(Path(sys.argv[1])):\n"
        "        pass\n"
        "except AccountInUse:\n"
        "    status = 2\n"
        "sys.exit(3 if attempts else status)\n"
    )
    with AccountLock(lock_path):
        blocked = subprocess.run(
            [sys.executable, "-c", script, str(lock_path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=environment,
        )
        assert blocked.returncode == 2, blocked.stderr

    released = subprocess.run(
        [sys.executable, "-c", script, str(lock_path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=environment,
    )
    assert released.returncode == 0, released.stderr
