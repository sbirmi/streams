ALTER TABLE streams RENAME COLUMN position TO order_key;

DROP INDEX IF EXISTS streams_by_bundle;
DROP INDEX IF EXISTS streams_by_parent;

WITH ranked AS (
    SELECT id,
           (ROW_NUMBER() OVER (
               PARTITION BY bundle_id, parent_stream_id
               ORDER BY order_key, created_at, id
           ) - 1) * 1000 + 1000 AS new_order_key
    FROM streams
)
UPDATE streams
SET order_key = (
    SELECT ranked.new_order_key
    FROM ranked
    WHERE ranked.id = streams.id
);

CREATE INDEX streams_by_bundle ON streams(bundle_id, order_key, created_at);
CREATE INDEX streams_by_parent ON streams(parent_stream_id, order_key, created_at);
