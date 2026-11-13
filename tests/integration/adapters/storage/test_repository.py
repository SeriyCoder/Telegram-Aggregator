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
from telegram_knowledge_base.domain.models import Post, Progress, Source


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)
    return Repository(database)


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
