"""Persistence operations for the initial Stream data model."""

from __future__ import annotations

import json
import re
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


def _normalize_owners(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError("owners must be a list")
    owners: list[str] = []
    for owner in value:
        if not isinstance(owner, str):
            raise ValueError("owners must contain only strings")
        owner = owner.strip()
        if owner:
            owners.append(owner)
    return owners


def _normalize_deadline(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", value):
        raise ValueError("deadline must be a date in YYYY-MM-DD or YYYY/MM/DD format")
    value = value.replace("/", "-")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("deadline must be a valid date") from error
    return value


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError("tags must be a list")
    tags: list[str] = []
    for tag in value:
        if not isinstance(tag, str):
            raise ValueError("tags must contain only strings")
        tag = tag.strip()
        if tag:
            tags.append(tag)
    return tags


def _normalize_favorite(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("favorite must be a boolean")
    return value


VALID_STATUSES = {"open", "resolved", "no_action"}


def _normalize_status(value: Any) -> str:
    if value == "no-action":
        value = "no_action"
    if not isinstance(value, str) or value not in VALID_STATUSES:
        raise ValueError("status must be one of: open, resolved, no_action")
    return value


def _decode(row: Any) -> dict[str, Any]:
    result = dict(row)
    for field in ("owners", "tags"):
        if field in result:
            result[field] = json.loads(result[field])
    if "favorite" in result:
        result["favorite"] = bool(result["favorite"])
    return result


class Repository:
    """Application-facing repository using short SQLite transactions."""

    def __init__(self, database: Database):
        self.database = database

    def create_bundle(self, name: str, creator: str, description: str = "", bundle_id: str | None = None) -> dict[str, Any]:
        bundle_id = bundle_id or new_id()
        timestamp = now()
        with self.database.transaction() as connection:
            self._begin_transaction(connection, creator, "create_bundle", f"Created bundle {name}")
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
        root_stream_id: str | None = None,
    ) -> dict[str, Any]:
        stream_id = stream_id or new_id()
        timestamp = now()
        owners = _normalize_owners(owners)
        deadline = _normalize_deadline(deadline)
        tags = _normalize_tags(tags)
        with self.database.transaction() as connection:
            self._begin_transaction(connection, creator, "create_stream", f"Created stream {summary}")
            self._require_bundle(connection, bundle_id)
            if root_stream_id:
                root = self._require_stream(connection, root_stream_id, bundle_id=bundle_id)
                if placement in {"before", "after"}:
                    if not anchor_stream_id or anchor_stream_id == root_stream_id or not self._is_within_root(
                        connection, anchor_stream_id, root_stream_id
                    ):
                        raise ValueError("sibling insertion must remain inside the rooted view")
                elif placement == "child" and parent_stream_id and not self._is_within_root(
                    connection, parent_stream_id, root_stream_id
                ):
                    raise ValueError("child insertion must remain inside the rooted view")
            if parent_stream_id:
                self._require_stream(connection, parent_stream_id, bundle_id=bundle_id)
            order_key = self._insertion_order_key(
                connection, bundle_id, parent_stream_id, anchor_stream_id, placement
            )
            connection.execute(
                "INSERT INTO streams("
                "id, bundle_id, parent_stream_id, summary, description, owners, creator, priority, "
                "snooze_until, deadline, created_at, updated_at, closed_at, close_status, tags, revision, order_key"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 1, 0)",
                (stream_id, bundle_id, parent_stream_id, summary, description, _json(owners), creator, priority,
                 snooze_until, deadline, timestamp, timestamp, _json(tags)),
            )
            connection.execute("UPDATE streams SET order_key = ? WHERE id = ?", (order_key, stream_id))
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
            query += " AND status = 'open'"
        query += " ORDER BY order_key, created_at, id"
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
                   "status", "tags", "parent_stream_id", "favorite"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unsupported stream fields: {sorted(unknown)}")
        changes = dict(changes)
        if "owners" in changes:
            changes["owners"] = _normalize_owners(changes["owners"])
        if "deadline" in changes:
            changes["deadline"] = _normalize_deadline(changes["deadline"])
        if "tags" in changes:
            changes["tags"] = _normalize_tags(changes["tags"])
        if "favorite" in changes:
            changes["favorite"] = _normalize_favorite(changes["favorite"])
        if "status" in changes:
            changes["status"] = _normalize_status(changes["status"])
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "update_stream", "Updated stream")
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

    def update_stream_statuses(
        self, stream_ids: list[str], revisions: dict[str, int], status: str, actor: str
    ) -> list[dict[str, Any]]:
        """Set one status on one or more streams atomically with revision checks."""

        if not stream_ids:
            raise ValueError("stream_ids must not be empty")
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream_ids must be unique")
        status = _normalize_status(status)
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "bulk_status", f"Changed status on {len(stream_ids)} streams")
            rows = [self._require_stream(connection, stream_id) for stream_id in stream_ids]
            current_values = {row["id"]: _decode(row) for row in rows}
            for stream_id in stream_ids:
                expected = revisions.get(stream_id)
                if not isinstance(expected, int):
                    raise ValueError("a revision is required for every stream")
                self._check_revision("stream", stream_id, current_values[stream_id], expected)

            timestamp = now()
            updated: list[dict[str, Any]] = []
            for stream_id in stream_ids:
                current = current_values[stream_id]
                if current["status"] == status:
                    updated.append(current)
                    continue
                connection.execute(
                    "UPDATE streams SET status = ?, updated_at = ?, revision = revision + 1 "
                    "WHERE id = ? AND revision = ?",
                    (status, timestamp, stream_id, current["revision"]),
                )
                after = _decode(self._require_stream(connection, stream_id))
                self._record_history(connection, "stream", stream_id, actor, current, after)
                updated.append(after)
            return updated

    def delete_stream(self, stream_id: str, expected_revision: int, actor: str) -> dict[str, Any]:
        """Delete one stream, promote its children to roots, and retain audit history."""

        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "delete_stream", "Deleted stream")
            current = _decode(self._require_stream(connection, stream_id))
            self._check_revision("stream", stream_id, current, expected_revision)
            child_rows = connection.execute(
                "SELECT * FROM streams WHERE parent_stream_id = ? ORDER BY order_key, created_at, id",
                (stream_id,),
            ).fetchall()
            children = [_decode(row) for row in child_rows]
            comment_rows = connection.execute(
                "SELECT * FROM comments WHERE stream_id = ? ORDER BY created_at, id", (stream_id,)
            ).fetchall()

            # Record the related deletes before the foreign-key cascade removes comments.
            for row in comment_rows:
                self._record_history(connection, "comment", row["id"], actor, dict(row), None)

            # Use the deleted stream's old order to place promoted children between roots.
            roots_before = [row[0] for row in connection.execute(
                "SELECT id FROM streams WHERE bundle_id = ? AND parent_stream_id IS NULL "
                "AND order_key < ? ORDER BY order_key, created_at, id",
                (current["bundle_id"], current["order_key"]),
            ).fetchall()]
            roots_after = [row[0] for row in connection.execute(
                "SELECT id FROM streams WHERE bundle_id = ? AND parent_stream_id IS NULL "
                "AND order_key > ? ORDER BY order_key, created_at, id",
                (current["bundle_id"], current["order_key"]),
            ).fetchall()]
            promoted_ids: list[str] = []
            for child in children:
                promoted = dict(child)
                promoted["parent_stream_id"] = None
                promoted["order_key"] = 0
                promoted["updated_at"] = now()
                promoted["revision"] = child["revision"] + 1
                connection.execute(
                    "UPDATE streams SET parent_stream_id = NULL, order_key = 0, updated_at = ?, revision = revision + 1 "
                    "WHERE id = ?",
                    (promoted["updated_at"], child["id"]),
                )
                self._record_history(connection, "stream", child["id"], actor, child, promoted)
                promoted_ids.append(child["id"])

            self._assign_order_keys(connection, roots_before + promoted_ids + roots_after)

            result = connection.execute(
                "DELETE FROM streams WHERE id = ? AND revision = ?", (stream_id, expected_revision)
            )
            if result.rowcount != 1:
                latest = _decode(self._require_stream(connection, stream_id))
                raise RevisionConflict("stream", stream_id, latest)
            self._record_history(connection, "stream", stream_id, actor, current, None)
            return current

    def move_streams(
        self,
        stream_ids: list[str],
        revisions: dict[str, int],
        target_stream_id: str,
        placement: str,
        actor: str,
        root_stream_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Move a contiguous sibling block atomically, preserving its order."""

        if not stream_ids:
            raise ValueError("stream_ids must not be empty")
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream_ids must be unique")
        if placement not in {"before", "after", "child"}:
            raise ValueError("placement must be before, after, or child")
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "move_streams", f"Moved {len(stream_ids)} streams")
            rows = [self._require_stream(connection, stream_id) for stream_id in stream_ids]
            bundle_id = rows[0]["bundle_id"]
            if any(row["bundle_id"] != bundle_id for row in rows):
                raise ValueError("moved streams must belong to one bundle")
            target_row = self._require_stream(connection, target_stream_id, bundle_id=bundle_id)
            target = _decode(target_row)
            for row in rows:
                current = _decode(row)
                expected = revisions.get(row["id"])
                if not isinstance(expected, int):
                    raise ValueError("a revision is required for every moved stream")
                self._check_revision("stream", row["id"], current, expected)
                if self._is_descendant(connection, target_stream_id, row["id"]):
                    raise ValueError("a stream cannot be moved beneath its descendant")
                if root_stream_id and not self._is_within_root(connection, row["id"], root_stream_id):
                    raise ValueError("moved stream must remain inside the rooted view")
            if root_stream_id:
                self._require_stream(connection, root_stream_id, bundle_id=bundle_id)
                if not self._is_within_root(connection, target_stream_id, root_stream_id):
                    raise ValueError("move target must remain inside the rooted view")
                if placement in {"before", "after"} and target_stream_id == root_stream_id:
                    raise ValueError("cannot move beside the rooted stream")

            parents = {row["parent_stream_id"] for row in rows}
            if len(parents) != 1:
                raise ValueError("moved streams must be siblings")
            source_parent = rows[0]["parent_stream_id"]
            sibling_rows = connection.execute(
                "SELECT * FROM streams WHERE bundle_id = ? AND parent_stream_id IS ? "
                "ORDER BY order_key, created_at, id", (bundle_id, source_parent)
            ).fetchall()
            sibling_ids = [row["id"] for row in sibling_rows]
            source_indexes = sorted(sibling_ids.index(stream_id) for stream_id in stream_ids)
            if source_indexes != list(range(source_indexes[0], source_indexes[-1] + 1)):
                raise ValueError("moved streams must be contiguous siblings")

            new_parent = target_stream_id if placement == "child" else target["parent_stream_id"]
            destination_rows = connection.execute(
                "SELECT id FROM streams WHERE bundle_id = ? AND parent_stream_id IS ? "
                "ORDER BY order_key, created_at, id", (bundle_id, new_parent)
            ).fetchall()
            destination_ids = [row["id"] for row in destination_rows]
            remaining = [stream_id for stream_id in sibling_ids if stream_id not in stream_ids]
            if new_parent != source_parent:
                remaining = destination_ids
            if placement == "child":
                insert_at = len(remaining)
            else:
                if target_stream_id not in remaining:
                    raise ValueError("move target cannot be part of the moved block")
                target_index = remaining.index(target_stream_id)
                insert_at = target_index if placement == "before" else target_index + 1
            result_ids = remaining[:insert_at] + stream_ids + remaining[insert_at:]
            if new_parent == source_parent and result_ids == sibling_ids:
                return [_decode(self._require_stream(connection, stream_id)) for stream_id in stream_ids]

            affected_ids = list(dict.fromkeys(sibling_ids + destination_ids + result_ids))
            before = {stream_id: _decode(self._require_stream(connection, stream_id)) for stream_id in affected_ids}
            timestamp = now()
            for index, stream_id in enumerate(result_ids, start=1):
                parent = new_parent if stream_id in stream_ids else before[stream_id]["parent_stream_id"]
                connection.execute(
                    "UPDATE streams SET parent_stream_id = ?, order_key = ?, updated_at = ?, revision = revision + 1 "
                    "WHERE id = ?", (parent, index * 1000, timestamp, stream_id)
                )
            # Reassign the old sibling list when moving across parents.
            if new_parent != source_parent:
                old_remaining = [stream_id for stream_id in sibling_ids if stream_id not in stream_ids]
                for index, stream_id in enumerate(old_remaining, start=1):
                    connection.execute(
                        "UPDATE streams SET order_key = ?, updated_at = ?, revision = revision + 1 WHERE id = ?",
                        (index * 1000, timestamp, stream_id)
                    )
            updated: list[dict[str, Any]] = []
            for stream_id in affected_ids:
                after = _decode(self._require_stream(connection, stream_id))
                if before[stream_id] != after:
                    self._record_history(connection, "stream", stream_id, actor, before[stream_id], after)
                if stream_id in stream_ids:
                    updated.append(after)
            return updated

    def delete_streams(self, stream_ids: list[str], revisions: dict[str, int], actor: str) -> list[str]:
        """Delete selected sibling roots and their complete subtrees atomically."""

        if not stream_ids:
            raise ValueError("stream_ids must not be empty")
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream_ids must be unique")
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "delete_streams", f"Deleted {len(stream_ids)} streams")
            roots = [self._require_stream(connection, stream_id) for stream_id in stream_ids]
            bundle_id = roots[0]["bundle_id"]
            if any(row["bundle_id"] != bundle_id for row in roots):
                raise ValueError("deleted streams must belong to one bundle")
            parent_ids = {row["parent_stream_id"] for row in roots}
            if len(parent_ids) != 1:
                raise ValueError("deleted streams must be siblings")
            sibling_rows = connection.execute(
                "SELECT id FROM streams WHERE bundle_id = ? AND parent_stream_id IS ? "
                "ORDER BY order_key, created_at, id", (bundle_id, roots[0]["parent_stream_id"])
            ).fetchall()
            sibling_ids = [row["id"] for row in sibling_rows]
            indexes = sorted(sibling_ids.index(stream_id) for stream_id in stream_ids)
            if indexes != list(range(indexes[0], indexes[-1] + 1)):
                raise ValueError("deleted streams must be contiguous siblings")

            subtree_ids: list[str] = []
            def collect(stream_id: str) -> None:
                subtree_ids.append(stream_id)
                children = connection.execute(
                    "SELECT id FROM streams WHERE parent_stream_id = ? ORDER BY order_key, created_at, id",
                    (stream_id,),
                ).fetchall()
                for child in children:
                    collect(child["id"])

            for root in roots:
                collect(root["id"])
            snapshots = {stream_id: _decode(self._require_stream(connection, stream_id)) for stream_id in subtree_ids}
            for stream_id in subtree_ids:
                expected = revisions.get(stream_id)
                if not isinstance(expected, int):
                    raise ValueError("a revision is required for every stream in the selected subtrees")
                self._check_revision("stream", stream_id, snapshots[stream_id], expected)
            comment_rows = connection.execute(
                "SELECT * FROM comments WHERE stream_id IN ({}) ORDER BY created_at, id".format(
                    ",".join("?" for _ in subtree_ids)
                ), subtree_ids,
            ).fetchall()
            for row in comment_rows:
                self._record_history(connection, "comment", row["id"], actor, dict(row), None)
            for stream_id in reversed(subtree_ids):
                connection.execute("DELETE FROM streams WHERE id = ? AND revision = ?", (stream_id, revisions[stream_id]))
            remaining = [stream_id for stream_id in sibling_ids if stream_id not in stream_ids]
            self._assign_order_keys(connection, remaining)
            for stream_id in reversed(subtree_ids):
                self._record_history(connection, "stream", stream_id, actor, snapshots[stream_id], None)
            return subtree_ids

    def add_comment(self, stream_id: str, body: str, creator: str, comment_id: str | None = None,
                    sticky_note: bool = False) -> dict[str, Any]:
        comment_id = comment_id or new_id()
        timestamp = now()
        with self.database.transaction() as connection:
            self._begin_transaction(connection, creator, "create_comment", "Added comment")
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
                # The comment rail indexes zero as the newest comment.  The id
                # tie-breaker keeps ordering deterministic for same-second writes.
                "SELECT * FROM comments WHERE stream_id = ? ORDER BY created_at DESC, id DESC", (stream_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def update_comment(self, comment_id: str, expected_revision: int, actor: str, body: str,
                       sticky_note: bool | None = None) -> dict[str, Any]:
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "update_comment", "Updated comment")
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

    def delete_comment(self, comment_id: str, expected_revision: int, actor: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            self._begin_transaction(connection, actor, "delete_comment", "Deleted comment")
            current = dict(self._require_comment(connection, comment_id))
            self._check_revision("comment", comment_id, current, expected_revision)
            result = connection.execute(
                "DELETE FROM comments WHERE id = ? AND revision = ?", (comment_id, expected_revision)
            )
            if result.rowcount != 1:
                latest = dict(self._require_comment(connection, comment_id))
                raise RevisionConflict("comment", comment_id, latest)
            self._record_history(connection, "comment", comment_id, actor, current, None)
            return current

    def list_transactions(
        self,
        limit: int = 100,
        query: str | None = None,
        actor: str | None = None,
        kind: str | None = None,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return searchable durable transaction envelopes, newest first."""
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be positive")
        clauses: list[str] = []
        parameters: list[Any] = []
        if query:
            clauses.append("(summary LIKE ? COLLATE NOCASE OR actor LIKE ? COLLATE NOCASE)")
            pattern = f"%{query}%"
            parameters.extend((pattern, pattern))
        if actor:
            clauses.append("actor = ?")
            parameters.append(actor)
        if kind:
            if kind not in {"mutation", "undo", "redo"}:
                raise ValueError("kind must be mutation, undo, or redo")
            clauses.append("kind = ?")
            parameters.append(kind)
        if state:
            if state not in {"active", "undone", "abandoned"}:
                raise ValueError("state must be active, undone, or abandoned")
            clauses.append("state = ?")
            parameters.append(state)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(limit)
        with self.database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM transactions" + where + " ORDER BY rowid DESC LIMIT ?", parameters
            ).fetchall()
            transactions = [dict(row) for row in rows]
            if not transactions:
                return []
            transaction_ids = [item["id"] for item in transactions]
            placeholders = ",".join("?" for _ in transaction_ids)
            history_rows = connection.execute(
                f"SELECT transaction_id, object_type, object_id, changed_fields, before_value, after_value "
                f"FROM history WHERE transaction_id IN ({placeholders}) ORDER BY sequence, rowid",
                transaction_ids,
            ).fetchall()

        changes_by_transaction: dict[str, list[dict[str, Any]]] = {item["id"]: [] for item in transactions}
        hidden_fields = {"revision", "updated_at", "created_at", "closed_at"}
        for row in history_rows:
            before = json.loads(row["before_value"]) if row["before_value"] else None
            after = json.loads(row["after_value"]) if row["after_value"] else None
            for field in json.loads(row["changed_fields"]):
                if field in hidden_fields:
                    continue
                snapshot = after or before or {}
                changes_by_transaction[row["transaction_id"]].append({
                    "object_type": row["object_type"],
                    "object_id": row["object_id"],
                    "object_summary": snapshot.get("summary") or snapshot.get("body"),
                    "field": field,
                    "before": (before or {}).get(field),
                    "after": (after or {}).get(field),
                })
        for transaction in transactions:
            transaction["changes"] = changes_by_transaction[transaction["id"]]
        return transactions

    def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        with self.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
            if row is None:
                raise NotFound(f"transaction {transaction_id}")

            transaction = dict(row)
            history_rows = connection.execute(
                "SELECT * FROM history WHERE transaction_id = ? ORDER BY sequence, rowid",
                (transaction_id,),
            ).fetchall()
            history: list[dict[str, Any]] = []
            for history_row in history_rows:
                item = dict(history_row)
                item["changed_fields"] = json.loads(item["changed_fields"])
                item["before_value"] = json.loads(item["before_value"]) if item["before_value"] else None
                item["after_value"] = json.loads(item["after_value"]) if item["after_value"] else None
                history.append(item)

            hidden_fields = {"revision", "updated_at", "created_at", "closed_at"}
            changes = []
            for item in history:
                before = item["before_value"] or {}
                after = item["after_value"] or {}
                snapshot = after or before
                for field in item["changed_fields"]:
                    if field in hidden_fields:
                        continue
                    changes.append({
                        "object_type": item["object_type"],
                        "object_id": item["object_id"],
                        "object_summary": snapshot.get("summary") or snapshot.get("body"),
                        "field": field,
                        "before": before.get(field),
                        "after": after.get(field),
                    })

            related_objects = []
            for item in history:
                snapshot = item["after_value"] or item["before_value"] or {}
                related_objects.append({
                    "object_type": item["object_type"],
                    "object_id": item["object_id"],
                    "exists_in_snapshot": item["after_value"] is not None,
                    "summary": snapshot.get("summary") or snapshot.get("body"),
                    "current_revision": snapshot.get("revision"),
                })
            transaction["history"] = history
            transaction["changes"] = changes
            transaction["related_objects"] = related_objects
            return transaction

    def get_transaction_state(self) -> dict[str, Any]:
        """Return the shared logical transaction position for the view bar.

        Undo leaves the targeted mutation in ``undone`` state, which marks the
        workspace as being at an older logical position.  A redo restores that
        mutation to ``active``; a new mutation abandons undone mutations and
        therefore establishes a new head.
        """
        with self.database.read() as connection:
            undone = connection.execute(
                "SELECT * FROM transactions "
                "WHERE kind = 'mutation' AND state = 'undone' "
                "ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if undone is not None:
                transaction = dict(undone)
                return {
                    "at_head": False,
                    "mode": "historical",
                    "transaction": {
                        "id": transaction["id"],
                        "actor": transaction["actor"],
                        "created_at": transaction["created_at"],
                        "action_type": transaction["action_type"],
                        "summary": transaction["summary"],
                        "kind": transaction["kind"],
                        "state": transaction["state"],
                    },
                }

            head = connection.execute(
                "SELECT * FROM transactions "
                "WHERE kind = 'mutation' AND state = 'active' "
                "ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            transaction = dict(head) if head is not None else None
            return {
                "at_head": True,
                "mode": "head",
                "transaction": ({
                    "id": transaction["id"],
                    "actor": transaction["actor"],
                    "created_at": transaction["created_at"],
                    "action_type": transaction["action_type"],
                    "summary": transaction["summary"],
                    "kind": transaction["kind"],
                    "state": transaction["state"],
                } if transaction is not None else None),
            }

    def undo_latest(self, actor: str, transaction_id: str | None = None) -> dict[str, Any]:
        return self._reverse_latest(actor, redo=False, transaction_id=transaction_id)

    def redo_latest(self, actor: str, transaction_id: str | None = None) -> dict[str, Any]:
        return self._reverse_latest(actor, redo=True, transaction_id=transaction_id)

    def _reverse_latest(self, actor: str, redo: bool, transaction_id: str | None = None) -> dict[str, Any]:
        with self.database.transaction() as connection:
            if redo:
                row = connection.execute(
                    "SELECT target.* FROM transactions AS undo "
                    "JOIN transactions AS target ON target.id = undo.target_transaction_id "
                    "WHERE undo.kind = 'undo' AND target.kind = 'mutation' AND target.state = 'undone' "
                    "AND (? IS NULL OR target.id = ?) ORDER BY undo.rowid DESC LIMIT 1",
                    (transaction_id, transaction_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM transactions WHERE kind = 'mutation' AND state = 'active' "
                    "AND (? IS NULL OR id = ?) ORDER BY rowid DESC LIMIT 1",
                    (transaction_id, transaction_id),
                ).fetchone()
            if row is None:
                raise ValueError("nothing to redo" if redo else "nothing to undo")
            target = dict(row)
            operation = self._begin_transaction(
                connection, actor, "redo" if redo else "undo",
                ("Redid " if redo else "Undid ") + target["summary"],
                kind="redo" if redo else "undo", target_transaction_id=target["id"],
            )
            entries = connection.execute(
                "SELECT * FROM history WHERE transaction_id = ? ORDER BY sequence",
                (target["id"],),
            ).fetchall()
            if not entries:
                raise ValueError("transaction has no history")
            decoded = []
            for entry in entries:
                item = dict(entry)
                item["before_value"] = json.loads(item["before_value"]) if item["before_value"] else None
                item["after_value"] = json.loads(item["after_value"]) if item["after_value"] else None
                expected = item["before_value"] if redo else item["after_value"]
                current = self._current_snapshot(connection, item["object_type"], item["object_id"])
                if not self._snapshot_matches(current, expected):
                    raise RevisionConflict(item["object_type"], item["object_id"], current or {})
                decoded.append((item, current, item["after_value"] if redo else item["before_value"]))

            # Restore parents before children; remove children/comments before parents.
            ordered = sorted(decoded, key=lambda value: 0 if value[2] is not None else 1)
            for item, current, desired in ordered:
                self._apply_snapshot(connection, item["object_type"], item["object_id"], current, desired)
                self._record_history(connection, item["object_type"], item["object_id"], actor, current, desired)
            connection.execute(
                "UPDATE transactions SET state = ? WHERE id = ?",
                ("active" if redo else "undone", target["id"]),
            )
            result = self._transaction(connection, operation)
            result["original_transaction"] = target
            result["focus"] = {"stream_id": next(
                (item["object_id"] for item, _, _ in decoded if item["object_type"] == "stream"), None
            )}
            return result

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
    def _begin_transaction(connection: Any, actor: str, action_type: str, summary: str,
                           kind: str = "mutation", target_transaction_id: str | None = None) -> str:
        transaction_id = new_id()
        if kind == "mutation":
            connection.execute("UPDATE transactions SET state = 'abandoned' WHERE kind = 'mutation' AND state = 'undone'")
        connection.execute(
            "INSERT INTO transactions(id, actor, created_at, action_type, summary, kind, state, target_transaction_id) "
            "VALUES (?, ?, ?, ?, ?, ?, 'active', ?)",
            (transaction_id, actor, now(), action_type, summary, kind, target_transaction_id),
        )
        connection.execute("CREATE TEMP TABLE IF NOT EXISTS current_transaction (id TEXT NOT NULL)")
        connection.execute("DELETE FROM current_transaction")
        connection.execute("INSERT INTO current_transaction(id) VALUES (?)", (transaction_id,))
        return transaction_id

    @staticmethod
    def _transaction(connection: Any, transaction_id: str) -> dict[str, Any]:
        return dict(connection.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone())

    @staticmethod
    def _current_snapshot(connection: Any, object_type: str, object_id: str) -> dict[str, Any] | None:
        table = "streams" if object_type == "stream" else "comments"
        row = connection.execute(f"SELECT * FROM {table} WHERE id = ?", (object_id,)).fetchone()
        if row is None:
            return None
        return _decode(row) if object_type == "stream" else dict(row)

    @staticmethod
    def _snapshot_matches(current: dict[str, Any] | None, expected: dict[str, Any] | None) -> bool:
        if current is None or expected is None:
            return current is expected
        ignored = {"revision", "updated_at"}
        return {k: v for k, v in current.items() if k not in ignored} == {k: v for k, v in expected.items() if k not in ignored}

    @staticmethod
    def _apply_snapshot(connection: Any, object_type: str, object_id: str,
                        current: dict[str, Any] | None, desired: dict[str, Any] | None) -> None:
        table = "streams" if object_type == "stream" else "comments"
        if desired is None:
            if current is not None:
                connection.execute(f"DELETE FROM {table} WHERE id = ?", (object_id,))
            return
        revision = (current or {}).get("revision", desired.get("revision", 1)) + 1
        values = dict(desired)
        values["revision"] = revision
        values["updated_at"] = now()
        if object_type == "stream":
            columns = ["bundle_id", "parent_stream_id", "summary", "description", "owners", "creator", "priority", "snooze_until", "deadline", "created_at", "updated_at", "closed_at", "close_status", "tags", "revision", "order_key", "status"]
            if current is None:
                connection.execute("INSERT INTO streams(id, " + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in ["id"] + columns) + ")", tuple([object_id] + [_json(values[c]) if c in {"owners", "tags"} else values.get(c) for c in columns]))
            else:
                connection.execute("UPDATE streams SET " + ", ".join(f"{c} = ?" for c in columns) + " WHERE id = ?", tuple([_json(values[c]) if c in {"owners", "tags"} else values.get(c) for c in columns] + [object_id]))
        else:
            columns = ["stream_id", "body", "creator", "created_at", "updated_at", "sticky_note", "revision"]
            if current is None:
                connection.execute("INSERT INTO comments(id, " + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in ["id"] + columns) + ")", tuple([object_id] + [values.get(c) for c in columns]))
            else:
                connection.execute("UPDATE comments SET " + ", ".join(f"{c} = ?" for c in columns) + " WHERE id = ?", tuple([values.get(c) for c in columns] + [object_id]))

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
    def _assign_order_keys(connection: Any, stream_ids: list[str]) -> None:
        for index, stream_id in enumerate(stream_ids, start=1):
            connection.execute(
                "UPDATE streams SET order_key = ? WHERE id = ?", (index * 1000, stream_id)
            )

    @staticmethod
    def _insertion_order_key(connection: Any, bundle_id: str, parent_stream_id: str | None,
                              anchor_stream_id: str | None, placement: str | None) -> int:
        siblings = connection.execute(
            "SELECT id, order_key FROM streams WHERE bundle_id = ? AND parent_stream_id IS ? "
            "ORDER BY order_key, created_at, id",
            (bundle_id, parent_stream_id),
        ).fetchall()
        if anchor_stream_id and placement in {"before", "after"}:
            anchor = Repository._require_stream(connection, anchor_stream_id, bundle_id=bundle_id)
            if anchor["parent_stream_id"] != parent_stream_id:
                raise ValueError("insertion anchor must share the new stream's parent")
            anchor_index = next(index for index, row in enumerate(siblings) if row["id"] == anchor_stream_id)
            lower_index = anchor_index if placement == "after" else anchor_index - 1
            upper_index = anchor_index + 1 if placement == "after" else anchor_index
            lower = siblings[lower_index]["order_key"] if lower_index >= 0 else None
            upper = siblings[upper_index]["order_key"] if upper_index < len(siblings) else None
        else:
            lower = siblings[-1]["order_key"] if siblings else None
            upper = None
        if lower is None:
            return (upper // 2) if upper is not None and upper > 1 else 1000
        if upper is None:
            return lower + 1000
        if upper - lower > 1:
            return lower + ((upper - lower) // 2)
        Repository._assign_order_keys(connection, [row["id"] for row in siblings])
        return Repository._insertion_order_key(connection, bundle_id, parent_stream_id, anchor_stream_id, placement)

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

    @classmethod
    def _is_within_root(cls, connection: Any, stream_id: str, root_id: str) -> bool:
        return stream_id == root_id or cls._is_descendant(connection, stream_id, root_id)

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
            "INSERT INTO history(id, object_type, object_id, actor, changed_at, changed_fields, before_value, after_value, transaction_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT id FROM current_transaction LIMIT 1))",
            (new_id(), object_type, object_id, actor, now(), _json(changed_fields), before_json, after_json),
        )
