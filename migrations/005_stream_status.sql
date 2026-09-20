ALTER TABLE streams ADD COLUMN status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'resolved', 'no_action'));

UPDATE streams
SET status = CASE
    WHEN close_status IN ('no-action', 'no_action', 'no action') THEN 'no_action'
    WHEN closed_at IS NOT NULL OR close_status IS NOT NULL THEN 'resolved'
    ELSE 'open'
END;
