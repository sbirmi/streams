CREATE TABLE bundles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    creator TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0)
);

CREATE TABLE streams (
    id TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    parent_stream_id TEXT REFERENCES streams(id) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    owners TEXT NOT NULL DEFAULT '[]',
    creator TEXT NOT NULL,
    priority INTEGER CHECK (priority >= 0),
    snooze_until TEXT,
    deadline TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    close_status TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    position INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX streams_by_bundle ON streams(bundle_id, position, created_at);
CREATE INDEX streams_by_parent ON streams(parent_stream_id, position, created_at);

CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    stream_id TEXT NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    creator TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    sticky_note INTEGER NOT NULL DEFAULT 0 CHECK (sticky_note IN (0, 1)),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0)
);

CREATE INDEX comments_by_stream ON comments(stream_id, created_at, id);

CREATE TABLE history (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    changed_fields TEXT NOT NULL,
    before_value TEXT,
    after_value TEXT
);

CREATE INDEX history_by_object ON history(object_type, object_id, sequence);
