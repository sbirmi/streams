CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    action_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'mutation'
        CHECK (kind IN ('mutation', 'undo', 'redo')),
    state TEXT NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'undone', 'abandoned')),
    target_transaction_id TEXT REFERENCES transactions(id)
);

CREATE INDEX transactions_by_created ON transactions(created_at, id);
CREATE INDEX transactions_by_state ON transactions(kind, state, created_at, id);

ALTER TABLE history ADD COLUMN transaction_id TEXT REFERENCES transactions(id);
CREATE INDEX history_by_transaction ON history(transaction_id, sequence);
