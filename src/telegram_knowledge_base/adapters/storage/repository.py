import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from telegram_knowledge_base.adapters.storage.lock import AccountLock
from telegram_knowledge_base.domain.filtering import (
    decode_cursor,
    encode_cursor,
    parse_search_tokens,
    validate_query,
)
from telegram_knowledge_base.domain.models import (
    FilterRule,
    Post,
    PostPage,
    PostQuery,
    PostRecord,
    Progress,
    Source,
    Tag,
    TagRule,
)


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

    def source_enabled(self, source_id: str) -> bool | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT enabled FROM sources WHERE telegram_id = ?", (source_id,)
            ).fetchone()
        return None if row is None else bool(row[0])

    def save_import(self, source: Source, posts: list[Post]) -> int:
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT INTO sources (telegram_id, username, title) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT (telegram_id) DO UPDATE SET "
                "username = COALESCE(excluded.username, username), "
                "title = excluded.title",
                (source.telegram_id, source.username, source.title),
            )
            created = 0
            for post in posts:
                if post.message_id < 1 or not post.text or not post.published_at:
                    raise ValueError("Invalid post data.")
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO posts "
                    "(source_id, message_id, text, published_at) "
                    "SELECT id, ?, ?, ? FROM sources WHERE telegram_id = ?",
                    (
                        post.message_id,
                        post.text,
                        post.published_at,
                        source.telegram_id,
                    ),
                )
                created += cursor.rowcount
            return created

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

    def create_tag(self, name: str, key: str, color: str | None) -> Tag:
        try:
            with self._connection() as connection, connection:
                cursor = connection.execute(
                    "INSERT INTO tags (name, key, color) VALUES (?, ?, ?)",
                    (name, key, color),
                )
                return Tag(self._insert_id(cursor), name, key, color)
        except sqlite3.IntegrityError:
            raise ValueError("The tag key already exists.") from None

    def update_tag(self, tag_id: int, name: str, key: str, color: str | None) -> Tag:
        try:
            with self._connection() as connection, connection:
                cursor = connection.execute(
                    "UPDATE tags SET name = ?, key = ?, color = ? WHERE id = ?",
                    (name, key, color, tag_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("The selected tag does not exist.")
                return Tag(tag_id, name, key, color)
        except sqlite3.IntegrityError:
            raise ValueError("The tag key already exists.") from None

    def delete_tag(self, tag_id: int) -> None:
        with self._connection() as connection, connection:
            cursor = connection.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            if cursor.rowcount != 1:
                raise ValueError("The selected tag does not exist.")

    def list_tags(self) -> list[Tag]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, name, key, color FROM tags ORDER BY key, id"
            ).fetchall()
        return [Tag(row[0], row[1], row[2], row[3]) for row in rows]

    def create_tag_rule(self, tag_id: int, phrase: str) -> TagRule:
        with self._connection() as connection, connection:
            if not self._tag_exists(connection, tag_id):
                raise ValueError("The selected tag does not exist.")
            cursor = connection.execute(
                "INSERT INTO tag_rules (tag_id, phrase, enabled) VALUES (?, ?, 1)",
                (tag_id, phrase),
            )
            return TagRule(self._insert_id(cursor), tag_id, phrase)

    def set_tag_rule_enabled(self, rule_id: int, enabled: bool) -> TagRule:
        with self._connection() as connection, connection:
            row = connection.execute(
                "SELECT tag_id, phrase FROM tag_rules WHERE id = ?", (rule_id,)
            ).fetchone()
            if row is None:
                raise ValueError("The selected tag rule does not exist.")
            connection.execute(
                "UPDATE tag_rules SET enabled = ? WHERE id = ?",
                (int(enabled), rule_id),
            )
            return TagRule(rule_id, row[0], row[1], enabled)

    def delete_tag_rule(self, rule_id: int) -> None:
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM tag_rules WHERE id = ?", (rule_id,)
            )
            if cursor.rowcount != 1:
                raise ValueError("The selected tag rule does not exist.")

    def list_tag_rules(self, tag_id: int) -> list[TagRule]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, tag_id, phrase, enabled FROM tag_rules "
                "WHERE tag_id = ? ORDER BY id",
                (tag_id,),
            ).fetchall()
        return [TagRule(row[0], row[1], row[2], bool(row[3])) for row in rows]

    def create_filter_rule(self, kind: str, phrase: str) -> FilterRule:
        if kind not in {"include", "exclude"}:
            raise ValueError("The filter type is invalid.")
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "INSERT INTO filter_rules (kind, phrase, enabled) VALUES (?, ?, 1)",
                (kind, phrase),
            )
            return FilterRule(
                self._insert_id(cursor),
                cast(Literal["include", "exclude"], kind),
                phrase,
            )

    def set_filter_rule_enabled(self, rule_id: int, enabled: bool) -> FilterRule:
        with self._connection() as connection, connection:
            row = connection.execute(
                "SELECT kind, phrase FROM filter_rules WHERE id = ?", (rule_id,)
            ).fetchone()
            if row is None:
                raise ValueError("The selected filter rule does not exist.")
            connection.execute(
                "UPDATE filter_rules SET enabled = ? WHERE id = ?",
                (int(enabled), rule_id),
            )
            return FilterRule(
                rule_id,
                cast(Literal["include", "exclude"], row[0]),
                row[1],
                enabled,
            )

    def delete_filter_rule(self, rule_id: int) -> None:
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM filter_rules WHERE id = ?", (rule_id,)
            )
            if cursor.rowcount != 1:
                raise ValueError("The selected filter rule does not exist.")

    def list_filter_rules(self) -> list[FilterRule]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, kind, phrase, enabled FROM filter_rules ORDER BY id"
            ).fetchall()
        return [
            FilterRule(
                row[0],
                cast(Literal["include", "exclude"], row[1]),
                row[2],
                bool(row[3]),
            )
            for row in rows
        ]

    def set_manual_tag(
        self, source_id: str, message_id: int, tag_id: int, present: bool
    ) -> None:
        with self._connection() as connection, connection:
            post_id = self._post_source_key(connection, source_id, message_id)
            if post_id is None:
                raise ValueError("The selected post does not exist.")
            if not self._tag_exists(connection, tag_id):
                raise ValueError("The selected tag does not exist.")
            if present:
                connection.execute(
                    "INSERT OR IGNORE INTO manual_post_tags "
                    "(source_id, message_id, tag_id) VALUES (?, ?, ?)",
                    (post_id, message_id, tag_id),
                )
            else:
                connection.execute(
                    "DELETE FROM manual_post_tags "
                    "WHERE source_id = ? AND message_id = ? AND tag_id = ?",
                    (post_id, message_id, tag_id),
                )

    def set_bookmark(self, source_id: str, message_id: int, present: bool) -> None:
        with self._connection() as connection, connection:
            post_id = self._post_source_key(connection, source_id, message_id)
            if post_id is None:
                raise ValueError("The selected post does not exist.")
            if present:
                connection.execute(
                    "INSERT OR IGNORE INTO bookmarks "
                    "(source_id, message_id, created_at) VALUES (?, ?, ?)",
                    (
                        post_id,
                        message_id,
                        datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    ),
                )
            else:
                connection.execute(
                    "DELETE FROM bookmarks WHERE source_id = ? AND message_id = ?",
                    (post_id, message_id),
                )

    def query_posts(self, query: PostQuery) -> PostPage:
        query = validate_query(query)
        tokens = parse_search_tokens(query.text)
        conditions: list[str] = []
        parameters: list[object] = []
        if tokens:
            conditions.append(
                "posts.rowid IN (SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?)"
            )
            parameters.append(" AND ".join(f'"{token}"' for token in tokens))
        if query.source_id is not None:
            conditions.append("sources.telegram_id = ?")
            parameters.append(query.source_id)
        if query.published_from is not None:
            conditions.append("posts.published_at >= ?")
            parameters.append(query.published_from)
        if query.published_to is not None:
            conditions.append("posts.published_at <= ?")
            parameters.append(query.published_to)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            "SELECT posts.rowid, posts.source_id, sources.telegram_id, "
            "sources.title, posts.message_id, posts.text, posts.published_at, "
            "EXISTS (SELECT 1 FROM bookmarks "
            "WHERE bookmarks.source_id = posts.source_id "
            "AND bookmarks.message_id = posts.message_id) "
            "FROM posts JOIN sources ON sources.id = posts.source_id"
            f"{where}"
        )
        with self._connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            tag_rows = connection.execute(
                "SELECT id, name, key, color FROM tags ORDER BY key, id"
            ).fetchall()
            rule_rows = connection.execute(
                "SELECT tag_id, phrase FROM tag_rules WHERE enabled = 1"
            ).fetchall()
            filter_rows = connection.execute(
                "SELECT kind, phrase FROM filter_rules WHERE enabled = 1"
            ).fetchall()
            manual_rows = connection.execute(
                "SELECT source_id, message_id, tag_id FROM manual_post_tags"
            ).fetchall()
        tags = {row[0]: Tag(row[0], row[1], row[2], row[3]) for row in tag_rows}
        automatic_rules: dict[int, list[str]] = {}
        for tag_id, phrase in rule_rows:
            automatic_rules.setdefault(tag_id, []).append(phrase.casefold())
        manual_tags: dict[tuple[int, int], set[int]] = {}
        for source_db_id, message_id, tag_id in manual_rows:
            manual_tags.setdefault((source_db_id, message_id), set()).add(tag_id)
        include_phrases = [
            phrase.casefold() for kind, phrase in filter_rows if kind == "include"
        ]
        exclude_phrases = [
            phrase.casefold() for kind, phrase in filter_rows if kind == "exclude"
        ]
        records: list[PostRecord] = []
        for row in rows:
            _, source_db_id, telegram_id, title, message_id, text, published, marked = (
                row
            )
            folded_text = text.casefold()
            if include_phrases and not any(
                phrase in folded_text for phrase in include_phrases
            ):
                continue
            if any(phrase in folded_text for phrase in exclude_phrases):
                continue
            automatic_ids = {
                tag_id
                for tag_id, phrases in automatic_rules.items()
                if any(phrase in folded_text for phrase in phrases)
            }
            manual_ids = manual_tags.get((source_db_id, message_id), set())
            matched_ids = automatic_ids | manual_ids
            record_tags = tuple(tags[tag_id] for tag_id in sorted(matched_ids))
            if query.tag_keys and not any(
                tag.key in query.tag_keys for tag in record_tags
            ):
                continue
            if query.bookmarked_only and not marked:
                continue
            records.append(
                PostRecord(
                    telegram_id,
                    title or "",
                    Post(message_id, text, published),
                    record_tags,
                    frozenset(manual_ids),
                    bool(marked),
                )
            )
        records.sort(key=lambda record: (record.source_id, record.post.message_id))
        records.sort(key=lambda record: record.post.published_at, reverse=True)
        offset = decode_cursor(query.cursor)
        end = offset + query.limit
        return PostPage(
            records[offset:end],
            encode_cursor(end) if end < len(records) else None,
        )

    def has_password_verifier(self) -> bool:
        return self.get_password_verifier() is not None

    def save_password_verifier(self, verifier: str) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT INTO web_auth (id, verifier, created_at, updated_at) "
                "VALUES (1, ?, ?, ?)",
                (verifier, now, now),
            )

    def get_password_verifier(self) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT verifier FROM web_auth WHERE id = 1"
            ).fetchone()
        return str(row[0]) if row is not None else None

    def create_session(self, token_hash: str) -> None:
        now = datetime.now(UTC)
        expires = now + timedelta(hours=12)
        with self._connection() as connection, connection:
            connection.execute(
                "DELETE FROM web_sessions WHERE expires_at <= ?",
                (now.strftime("%Y-%m-%dT%H:%M:%SZ"),),
            )
            connection.execute(
                "INSERT INTO web_sessions (token_hash, expires_at, created_at) "
                "VALUES (?, ?, ?)",
                (
                    token_hash,
                    expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
            )

    def delete_session(self, token_hash: str) -> None:
        with self._connection() as connection, connection:
            connection.execute(
                "DELETE FROM web_sessions WHERE token_hash = ?", (token_hash,)
            )

    def session_exists(self, token_hash: str) -> bool:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connection() as connection, connection:
            connection.execute("DELETE FROM web_sessions WHERE expires_at <= ?", (now,))
            row = connection.execute(
                "SELECT 1 FROM web_sessions WHERE token_hash = ? AND expires_at > ?",
                (token_hash, now),
            ).fetchone()
        return row is not None

    def count_posts_by_source(self) -> dict[str, int]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT sources.telegram_id, COUNT(posts.message_id) "
                "FROM sources LEFT JOIN posts ON posts.source_id = sources.id "
                "GROUP BY sources.id ORDER BY sources.title, sources.telegram_id"
            ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

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

    @staticmethod
    def _tag_exists(connection: sqlite3.Connection, tag_id: int) -> bool:
        return (
            connection.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone()
            is not None
        )

    @staticmethod
    def _insert_id(cursor: sqlite3.Cursor) -> int:
        if cursor.lastrowid is None:
            raise sqlite3.DatabaseError("Could not read the created record identifier.")
        return cursor.lastrowid

    @staticmethod
    def _post_source_key(
        connection: sqlite3.Connection, source_id: str, message_id: int
    ) -> int | None:
        row = connection.execute(
            "SELECT posts.source_id FROM posts "
            "JOIN sources ON sources.id = posts.source_id "
            "WHERE sources.telegram_id = ? AND posts.message_id = ?",
            (source_id, message_id),
        ).fetchone()
        return int(row[0]) if row is not None else None

    def _connection(self) -> closing[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        return closing(connection)
