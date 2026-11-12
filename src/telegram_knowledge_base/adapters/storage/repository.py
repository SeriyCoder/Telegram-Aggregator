import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from telegram_knowledge_base.adapters.storage.lock import AccountLock
from telegram_knowledge_base.domain.models import Post, Progress, Source


@dataclass
class Repository:
    database: Path

    def save_source(self, source: Source) -> None:
        if not source.is_channel or not source.is_public or source.username is None:
            raise ValueError("Only public Telegram channels can be stored.")
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT INTO sources (telegram_id, username, title) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT (telegram_id) DO UPDATE SET "
                "username = excluded.username, title = excluded.title",
                (source.telegram_id, source.username, source.title),
            )

    def set_enabled(self, source_id: str, enabled: bool) -> None:
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "UPDATE sources SET enabled = ? WHERE telegram_id = ?",
                (int(enabled), source_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("The selected source does not exist.")

    def list_sources(self) -> list[Source]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT telegram_id, username, title, enabled "
                "FROM sources ORDER BY title, telegram_id"
            ).fetchall()
        return [
            Source(row[0], row[1], row[2] or "", True, True, bool(row[3]))
            for row in rows
        ]

    def is_enabled(self, source_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT enabled FROM sources WHERE telegram_id = ?", (source_id,)
            ).fetchone()
        return row is not None and bool(row[0])

    def commit_batch(
        self, source_id: str, posts: list[Post], progress: Progress
    ) -> None:
        if progress.next_direction not in {"older", "newer"}:
            raise ValueError("Invalid synchronization direction.")
        if progress.newest_id is not None and progress.newest_id < 1:
            raise ValueError("Invalid newest message identifier.")
        if progress.oldest_id is not None and progress.oldest_id < 1:
            raise ValueError("Invalid oldest message identifier.")
        with self._connection() as connection, connection:
            source = connection.execute(
                "SELECT 1 FROM sources WHERE telegram_id = ?", (source_id,)
            ).fetchone()
            if source is None:
                raise ValueError("The selected source does not exist.")
            for post in posts:
                if post.ephemeral:
                    continue
                if post.message_id < 1 or not post.published_at:
                    raise ValueError("Invalid post data.")
                connection.execute(
                    "INSERT OR IGNORE INTO posts "
                    "(source_id, message_id, text, published_at) "
                    "SELECT id, ?, ?, ? FROM sources WHERE telegram_id = ?",
                    (post.message_id, post.text, post.published_at, source_id),
                )
            connection.execute(
                "INSERT INTO sync_state "
                "(source_id, newest_id, oldest_id, backfill_complete, next_direction) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (source_id) DO UPDATE SET "
                "newest_id = excluded.newest_id, "
                "oldest_id = excluded.oldest_id, "
                "backfill_complete = excluded.backfill_complete, "
                "next_direction = excluded.next_direction",
                (
                    source_id,
                    progress.newest_id,
                    progress.oldest_id,
                    int(progress.backfill_complete),
                    progress.next_direction,
                ),
            )

    def get_progress(self, source_id: str) -> Progress:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT newest_id, oldest_id, backfill_complete, next_direction "
                "FROM sync_state WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            return Progress()
        return Progress(row[0], row[1], bool(row[2]), row[3])

    def list_posts(self, source_id: str) -> list[Post]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT posts.message_id, posts.text, posts.published_at "
                "FROM posts JOIN sources ON sources.id = posts.source_id "
                "WHERE sources.telegram_id = ? ORDER BY posts.message_id",
                (source_id,),
            ).fetchall()
        return [Post(row[0], row[1], row[2]) for row in rows]

    def count_posts(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) FROM posts").fetchone()
        if row is None:
            raise sqlite3.DatabaseError("Could not count stored posts.")
        return int(row[0])

    def get_cooldown(self) -> datetime | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT deadline_utc FROM api_cooldown WHERE id = 1"
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row is not None else None

    def set_cooldown(self, until: datetime) -> None:
        if until.tzinfo is None:
            raise ValueError("Cooldown deadline must include a timezone.")
        deadline = until.astimezone(UTC).isoformat()
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT INTO api_cooldown (id, deadline_utc) VALUES (1, ?) "
                "ON CONFLICT (id) DO UPDATE SET deadline_utc = excluded.deadline_utc",
                (deadline,),
            )

    def account_lock(self) -> "AccountLock":
        return AccountLock(self.database.with_name("telegram-account.lock"))

    def _connection(self) -> closing[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        return closing(connection)
