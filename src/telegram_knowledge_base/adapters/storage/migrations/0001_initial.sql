CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    telegram_id TEXT NOT NULL UNIQUE,
    username TEXT,
    title TEXT
);

CREATE TABLE posts (
    source_id INTEGER NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    published_at TEXT NOT NULL,
    PRIMARY KEY (source_id, message_id)
);

CREATE INDEX posts_published_at_idx ON posts (published_at);
