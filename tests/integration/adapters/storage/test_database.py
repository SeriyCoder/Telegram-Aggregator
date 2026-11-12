import sqlite3
from pathlib import Path

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
