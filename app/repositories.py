"""Persistence operations for the initial Stream data model."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from .db import Database


class RevisionConflict(Exception):
    """Raised when a write targets an object that has changed since it was read."""

    def __init__(self, object_type: str, object_id: str, current: dict[str, Any]):
        super().__init__(f"{object_type} {object_id} has changed")
        self.object_type = object_type
        self.object_id = object_id
        self.current = current


class NotFound(Exception):
    """Raised when a requested object does not exist."""


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _decode(row: Any) -> dict[str, Any]:
    result = dict(row)
    for field in ("owners", "tags"):
        if field in result:
            result[field] = json.loads(result[field])
    return result


class Repository:
    """Application-facing repository using short SQLite transactions."""

    def __init__(self, database: Database):
        self.database = database

    def create_bundle(self, name: str, creator: str, description: str = "", bundle_id: str | None = None) -> dict[str, Any]:
        bundle_id = bundle_id or new_id()
        timestamp = now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO bundles(id, name, description, creator, created_at, updated_at, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (bundle_id, name, description, creator, timestamp, timestamp),
            )
            row = connection.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)).fetchone()
            assert row is not None
            result = dict(row)
            self._record_history(connection, "bundle", bundle_id, creator, None, result)
            return result

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        with self.database.read() as connection:
            row = connection.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)).fetchone()
        if row is None:
            raise NotFound(f"bundle {bundle_id}")
        return dict(row)

    def list_bundles(self) -> list[dict[str, Any]]:
        with self.database.read() as connection:
            rows = connection.execute("SELECT * FROM bundles ORDER BY name, id").fetchall()
        return [dict(row) for row in rows]

    def create_stream(
        self,
        bundle_id: str,
        summary: str,
        creator: str,
        description: str = "",
        owners: Iterable[str] = (),
        priority: int | None = None,
        parent_stream_id: str | None = None,
        deadline: str | None = None,
        snooze_until: str | None = None,
        tags: Iterable[str] = (),
        stream_id: str | None = None,
        anchor_stream_id: str | None = None,
        placement: str | None = None,
    ) -> dict[str, Any]:
        stream_id = stream_id or new_id()
        timestamp = now()
        owners = list(owners)
        tags = list(tags)
        with self.database.transaction() as connection:
            self._require_bundle(connection, bundle_id)
            if parent_stream_id:
                self._require_stream(connection, parent_stream_id, bundle_id=bundle_id)
            position = self._insertion_position(
                connection, bundle_id, parent_stream_id, anchor_stream_id, placement
            )
            if anchor_stream_id and placement in {"before", "after"}:
                anchor = self._require_stream(connection, anchor_stream_id, bundle_id=bundle_id)
                if anchor["parent_stream_id"] != parent_stream_id:
                    raise ValueError("insertion anchor must share the new stream's parent")
                threshold = anchor["position"] + (1 if placement == "after" else 0)
                connection.execute(
                    "UPDATE streams SET position = position + 1 WHERE bundle_id = ? "
                    "AND parent_stream_id IS ? AND position >= ?",
                    (bundle_id, parent_stream_id, threshold),
                )
            connection.execute(
                "INSERT INTO streams("
                "id, bundle_id, parent_stream_id, summary, description, owners, creator, priority, "
                "snooze_until, deadline, created_at, updated_at, closed_at, close_status, tags, revision, position"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 1, 0)",
                (stream_id, bundle_id, parent_stream_id, summary, description, _json(owners), creator, priority,
                 snooze_until, deadline, timestamp, timestamp, _json(tags)),
            )
            connection.execute("UPDATE streams SET position = ? WHERE id = ?", (position, stream_id))
            row = connection.execute("SELECT * FROM streams WHERE id = ?", (stream_id,)).fetchone()
            assert row is not None
            result = _decode(row)
            self._record_history(connection, "stream", stream_id, creator, None, result)
            return result

    def get_stream(self, stream_id: str) -> dict[str, Any]:
        with self.database.read() as connection:
            row = connection.execute("SELECT * FROM streams WHERE id = ?", (stream_id,)).fetchone()
        if row is None:
            raise NotFound(f"stream {stream_id}")
        return _decode(row)

    def list_streams(self, bundle_id: str, include_closed: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM streams WHERE bundle_id = ?"
        parameters: list[Any] = [bundle_id]
        if not include_closed:
            query += " AND closed_at IS NULL"
        query += " ORDER BY position, created_at, id"
        with self.database.read() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_decode(row) for row in rows]

    def update_stream(
        self,
        stream_id: str,
        expected_revision: int,
        actor: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = {"summary", "description", "owners", "priority", "snooze_until", "deadline",
                   "closed_at", "close_status", "tags", "parent_stream_id", "position"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unsupported stream fields: {sorted(unknown)}")
        with self.database.transaction() as connection:
            current_row = self._require_stream(connection, stream_id)
            current = _decode(current_row)
            self._check_revision("stream", stream_id, current, expected_revision)
            if "parent_stream_id" in changes and changes["parent_stream_id"]:
                parent_id = changes["parent_stream_id"]
                self._require_stream(connection, parent_id, bundle_id=current["bundle_id"])
                if parent_id == stream_id or self._is_descendant(connection, parent_id, stream_id):
                    raise ValueError("a stream cannot be its own ancestor")
            assignments = []
            parameters: list[Any] = []
            for field, value in changes.items():
                assignments.append(f"{field} = ?")
                parameters.append(_json(value) if field in {"owners", "tags"} else value)
            assignments.extend(["updated_at = ?", "revision = revision + 1"])
            parameters.extend([now(), stream_id, expected_revision])
            result = connection.execute(
                f"UPDATE streams SET {', '.join(assignments)} WHERE id = ? AND revision = ?",
                parameters,
            )
            if result.rowcount != 1:
                latest = _decode(self._require_stream(connection, stream_id))
                raise RevisionConflict("stream", stream_id, latest)
            updated = _decode(self._require_stream(connection, stream_id))
            self._record_history(connection, "stream", stream_id, actor, current, updated)
            return updated

    def add_comment(self, stream_id: str, body: str, creator: str, comment_id: str | None = None,
                    sticky_note: bool = False) -> dict[str, Any]:
        comment_id = comment_id or new_id()
        timestamp = now()
        with self.database.transaction() as connection:
            self._require_stream(connection, stream_id)
            connection.execute(
                "INSERT INTO comments(id, stream_id, body, creator, created_at, updated_at, sticky_note, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (comment_id, stream_id, body, creator, timestamp, timestamp, int(sticky_note)),
            )
            connection.execute("UPDATE streams SET updated_at = ? WHERE id = ?", (timestamp, stream_id))
            row = connection.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
            assert row is not None
            result = dict(row)
            self._record_history(connection, "comment", comment_id, creator, None, result)
            return result

    def get_comment(self, comment_id: str) -> dict[str, Any]:
        with self.database.read() as connection:
            row = connection.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
        if row is None:
            raise NotFound(f"comment {comment_id}")
        return dict(row)

    def list_comments(self, stream_id: str) -> list[dict[str, Any]]:
        with self.database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM comments WHERE stream_id = ? ORDER BY created_at, id", (stream_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def update_comment(self, comment_id: str, expected_revision: int, actor: str, body: str,
                       sticky_note: bool | None = None) -> dict[str, Any]:
        with self.database.transaction() as connection:
            current_row = self._require_comment(connection, comment_id)
            current = dict(current_row)
            self._check_revision("comment", comment_id, current, expected_revision)
            fields = ["body = ?", "updated_at = ?", "revision = revision + 1"]
            parameters: list[Any] = [body, now()]
            if sticky_note is not None:
                fields.append("sticky_note = ?")
                parameters.append(int(sticky_note))
            parameters.extend([comment_id, expected_revision])
            result = connection.execute(
                f"UPDATE comments SET {', '.join(fields)} WHERE id = ? AND revision = ?", parameters
            )
            if result.rowcount != 1:
                latest = dict(self._require_comment(connection, comment_id))
                raise RevisionConflict("comment", comment_id, latest)
            updated = dict(self._require_comment(connection, comment_id))
            self._record_history(connection, "comment", comment_id, actor, current, updated)
            return updated

    def list_history(self, object_type: str, object_id: str) -> list[dict[str, Any]]:
        with self.database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM history WHERE object_type = ? AND object_id = ? ORDER BY sequence",
                (object_type, object_id),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["changed_fields"] = json.loads(item["changed_fields"])
            item["before_value"] = json.loads(item["before_value"]) if item["before_value"] else None
            item["after_value"] = json.loads(item["after_value"]) if item["after_value"] else None
            result.append(item)
        return result

    @staticmethod
    def _require_bundle(connection: Any, bundle_id: str) -> Any:
        row = connection.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)).fetchone()
        if row is None:
            raise NotFound(f"bundle {bundle_id}")
        return row

    @staticmethod
    def _require_stream(connection: Any, stream_id: str, bundle_id: str | None = None) -> Any:
        row = connection.execute("SELECT * FROM streams WHERE id = ?", (stream_id,)).fetchone()
        if row is None or (bundle_id is not None and row["bundle_id"] != bundle_id):
            raise NotFound(f"stream {stream_id}")
        return row

    @staticmethod
    def _require_comment(connection: Any, comment_id: str) -> Any:
        row = connection.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
        if row is None:
            raise NotFound(f"comment {comment_id}")
        return row

    @staticmethod
    def _insertion_position(connection: Any, bundle_id: str, parent_stream_id: str | None,
                            anchor_stream_id: str | None, placement: str | None) -> int:
        if anchor_stream_id and placement in {"before", "after"}:
            anchor = Repository._require_stream(connection, anchor_stream_id, bundle_id=bundle_id)
            return anchor["position"] + (1 if placement == "after" else 0)
        row = connection.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM streams WHERE bundle_id = ? AND parent_stream_id IS ?",
            (bundle_id, parent_stream_id),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _is_descendant(connection: Any, candidate_id: str, ancestor_id: str) -> bool:
        """Return whether candidate_id is below ancestor_id in the stream tree."""

        current_id = candidate_id
        while current_id is not None:
            row = connection.execute(
                "SELECT parent_stream_id FROM streams WHERE id = ?", (current_id,)
            ).fetchone()
            if row is None:
                return False
            current_id = row[0]
            if current_id == ancestor_id:
                return True
        return False

    @staticmethod
    def _check_revision(object_type: str, object_id: str, current: dict[str, Any], expected: int) -> None:
        if current["revision"] != expected:
            raise RevisionConflict(object_type, object_id, current)

    @staticmethod
    def _record_history(connection: Any, object_type: str, object_id: str, actor: str,
                        before: dict[str, Any] | None, after: dict[str, Any] | None) -> None:
        before_json = _json(before) if before is not None else None
        after_json = _json(after) if after is not None else None
        before_keys = set(before or {})
        after_keys = set(after or {})
        changed_fields = sorted(
            field for field in before_keys | after_keys
            if (before or {}).get(field) != (after or {}).get(field)
        )
        connection.execute(
            "INSERT INTO history(id, object_type, object_id, actor, changed_at, changed_fields, before_value, after_value) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), object_type, object_id, actor, now(), _json(changed_fields), before_json, after_json),
        )
