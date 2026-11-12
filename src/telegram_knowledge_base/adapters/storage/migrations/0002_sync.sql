ALTER TABLE sources
ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1));

CREATE TABLE sync_state (
    source_id TEXT PRIMARY KEY REFERENCES sources (telegram_id) ON DELETE CASCADE,
    newest_id INTEGER,
    oldest_id INTEGER,
    backfill_complete INTEGER NOT NULL DEFAULT 0
        CHECK (backfill_complete IN (0, 1)),
    next_direction TEXT NOT NULL DEFAULT 'older'
        CHECK (next_direction IN ('older', 'newer'))
);

CREATE TABLE api_cooldown (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    deadline_utc TEXT NOT NULL
);
