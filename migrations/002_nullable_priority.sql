PRAGMA foreign_keys = OFF;

CREATE TABLE streams_without_required_priority (
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

INSERT INTO streams_without_required_priority SELECT * FROM streams;
DROP TABLE streams;
ALTER TABLE streams_without_required_priority RENAME TO streams;

CREATE INDEX streams_by_bundle ON streams(bundle_id, position, created_at);
CREATE INDEX streams_by_parent ON streams(parent_stream_id, position, created_at);

PRAGMA foreign_keys = ON;
