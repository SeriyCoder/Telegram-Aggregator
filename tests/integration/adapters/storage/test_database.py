import sqlite3
from pathlib import Path
from typing import Any

import pytest


def test_reinitializing_a_database_preserves_existing_posts(tmp_path: Path) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)

    with sqlite3.connect(database) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        assert version > 0
        connection.execute(
            "INSERT INTO sources (id, telegram_id) VALUES (?, ?)", (1, 123)
        )
        connection.execute(
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (?, ?, ?, ?)",
            (1, 10, "example", "2026-01-01T00:00:00Z"),
        )

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == version
        assert connection.execute("SELECT text FROM posts").fetchall() == [("example",)]


def test_existing_unversioned_database_receives_initial_schema(tmp_path: Path) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    sqlite3.connect(database).close()

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] > 0
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"sources", "posts"} <= tables


def test_message_ids_are_unique_per_source(tmp_path: Path) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)

    with sqlite3.connect(database) as connection:
        connection.executemany(
            "INSERT INTO sources (id, telegram_id) VALUES (?, ?)", [(1, 123), (2, 456)]
        )
        insert = (
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (?, ?, ?, ?)"
        )
        connection.execute(insert, (1, 10, "first", "2026-01-01T00:00:00Z"))
        connection.execute(insert, (2, 10, "other source", "2026-01-01T00:00:00Z"))

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(insert, (1, 10, "duplicate", "2026-01-01T00:00:00Z"))


def test_newer_unknown_schema_is_rejected_without_changing_data(tmp_path: Path) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE preserved (value TEXT NOT NULL)")
        connection.execute("INSERT INTO preserved (value) VALUES (?)", ("keep",))
        connection.execute("PRAGMA user_version = 1000000")

    with pytest.raises(ValueError):
        initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1000000
        assert connection.execute("SELECT value FROM preserved").fetchall() == [
            ("keep",)
        ]


def test_version_one_database_is_migrated_without_losing_posts(tmp_path: Path) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    migration = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "telegram_knowledge_base"
        / "adapters"
        / "storage"
        / "migrations"
        / "0001_initial.sql"
    )
    with sqlite3.connect(database) as connection:
        connection.executescript(migration.read_text(encoding="utf-8"))
        connection.execute("PRAGMA user_version = 1")
        connection.execute("INSERT INTO sources (id, telegram_id) VALUES (1, '123')")
        connection.execute(
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (1, 10, 'preserved', '2026-01-01T00:00:00Z')"
        )

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] >= 2
        assert connection.execute("SELECT text FROM posts").fetchall() == [
            ("preserved",)
        ]


def test_version_two_database_backfills_search_and_knowledge_schema(
    tmp_path: Path,
) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    migrations = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "telegram_knowledge_base"
        / "adapters"
        / "storage"
        / "migrations"
    )
    with sqlite3.connect(database) as connection:
        connection.executescript((migrations / "0001_initial.sql").read_text("utf-8"))
        connection.executescript((migrations / "0002_sync.sql").read_text("utf-8"))
        connection.execute("PRAGMA user_version = 2")
        connection.execute("INSERT INTO sources (id, telegram_id) VALUES (1, '123')")
        connection.execute(
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (1, 10, 'Синтетический Python и SQLite', "
            "'2026-01-01T00:00:00Z')"
        )

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        assert {
            "tags",
            "tag_rules",
            "filter_rules",
            "manual_post_tags",
            "bookmarks",
            "posts_fts",
        } <= tables
        assert connection.execute(
            "SELECT COUNT(*) FROM posts_fts WHERE posts_fts MATCH 'python'"
        ).fetchone() == (1,)


def test_unavailable_fts5_rejects_migration_without_partial_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import telegram_knowledge_base.adapters.storage.sqlite as sqlite_module

    database = tmp_path / "knowledge.sqlite3"
    migrations = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "telegram_knowledge_base"
        / "adapters"
        / "storage"
        / "migrations"
    )
    with sqlite3.connect(database) as connection:
        connection.executescript((migrations / "0001_initial.sql").read_text("utf-8"))
        connection.executescript((migrations / "0002_sync.sql").read_text("utf-8"))
        connection.execute("PRAGMA user_version = 2")
        connection.execute("INSERT INTO sources (id, telegram_id) VALUES (1, '123')")
        connection.execute(
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (1, 10, 'preserved', '2026-01-01T00:00:00Z')"
        )

    original_connect = sqlite3.connect

    class NoFtsConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def __enter__(self) -> "NoFtsConnection":
            self.connection.__enter__()
            return self

        def __exit__(self, *args: Any) -> bool | None:
            return self.connection.__exit__(*args)

        def close(self) -> None:
            self.connection.close()

        def __getattr__(self, name: str) -> Any:
            return getattr(self.connection, name)

        def executescript(self, script: str) -> None:
            if "USING fts5" in script:
                raise sqlite3.OperationalError("FTS5 is unavailable")
            self.connection.executescript(script)

    def connect_without_fts(*args: Any, **kwargs: Any) -> NoFtsConnection:
        return NoFtsConnection(original_connect(*args, **kwargs))

    monkeypatch.setattr(sqlite_module.sqlite3, "connect", connect_without_fts)
    with pytest.raises(sqlite3.OperationalError, match="FTS5 is unavailable"):
        sqlite_module.initialize_database(database)

    monkeypatch.setattr(sqlite_module.sqlite3, "connect", original_connect)
    with original_connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        assert connection.execute("SELECT text FROM posts").fetchall() == [
            ("preserved",)
        ]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "tags" not in tables


def test_version_three_database_adds_web_auth_without_losing_knowledge(
    tmp_path: Path,
) -> None:
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database

    database = tmp_path / "knowledge.sqlite3"
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO sources (id, telegram_id, title) VALUES (1, '123', 'Local')"
        )
        connection.execute(
            "INSERT INTO posts (source_id, message_id, text, published_at) "
            "VALUES (1, 1, 'preserved post', '2026-01-01T00:00:00Z')"
        )
        connection.execute("INSERT INTO tags (name, key) VALUES ('Python', 'python')")

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (4,)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"web_auth", "web_sessions", "tags", "posts"} <= tables
        assert connection.execute("SELECT text FROM posts").fetchall() == [
            ("preserved post",)
        ]
        assert connection.execute("SELECT key FROM tags").fetchall() == [("python",)]
