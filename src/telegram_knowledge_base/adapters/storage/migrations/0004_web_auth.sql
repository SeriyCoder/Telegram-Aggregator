CREATE TABLE web_auth (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    verifier TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE web_sessions (
    token_hash TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX web_sessions_expires_at_idx ON web_sessions (expires_at);
