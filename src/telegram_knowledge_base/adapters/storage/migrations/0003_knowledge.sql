CREATE VIRTUAL TABLE posts_fts USING fts5(
    text,
    content = 'posts',
    content_rowid = 'rowid',
    tokenize = 'unicode61'
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    key TEXT NOT NULL UNIQUE,
    color TEXT
);

CREATE TABLE tag_rules (
    id INTEGER PRIMARY KEY,
    tag_id INTEGER NOT NULL REFERENCES tags (id) ON DELETE CASCADE,
    phrase TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE INDEX tag_rules_tag_id_idx ON tag_rules (tag_id);

CREATE TABLE filter_rules (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('include', 'exclude')),
    phrase TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE manual_post_tags (
    source_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL REFERENCES tags (id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, message_id, tag_id),
    FOREIGN KEY (source_id, message_id)
        REFERENCES posts (source_id, message_id) ON DELETE CASCADE
);

CREATE INDEX manual_post_tags_tag_id_idx ON manual_post_tags (tag_id);

CREATE TABLE bookmarks (
    source_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, message_id),
    FOREIGN KEY (source_id, message_id)
        REFERENCES posts (source_id, message_id) ON DELETE CASCADE
);

CREATE TRIGGER posts_fts_after_insert
AFTER INSERT ON posts
BEGIN
    INSERT INTO posts_fts (rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER posts_fts_after_delete
AFTER DELETE ON posts
BEGIN
    INSERT INTO posts_fts (posts_fts, rowid, text)
    VALUES ('delete', old.rowid, old.text);
END;

CREATE TRIGGER posts_fts_after_update
AFTER UPDATE OF text ON posts
BEGIN
    INSERT INTO posts_fts (posts_fts, rowid, text)
    VALUES ('delete', old.rowid, old.text);
    INSERT INTO posts_fts (rowid, text) VALUES (new.rowid, new.text);
END;

INSERT INTO posts_fts (posts_fts) VALUES ('rebuild');
