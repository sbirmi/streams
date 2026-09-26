"""Read-only checks for SQLite data that application writes cannot fully constrain."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


TABLES = {"bundles", "streams", "comments", "history", "transactions"}
STREAM_STATUSES = {"open", "resolved", "no_action"}


def _label(value: Any) -> str:
    return "<root>" if value is None else str(value)


def _json_array_issues(table: str, row: sqlite3.Row, column: str) -> list[str]:
    try:
        value = json.loads(row[column])
    except (TypeError, json.JSONDecodeError) as error:
        return [f"{table} {row['id']} has invalid {column} JSON: {error}"]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return [f"{table} {row['id']} has non-string-array {column} JSON"]
    return []


def _check_streams(connection: sqlite3.Connection) -> list[str]:
    issues: list[str] = []
    rows = connection.execute("SELECT * FROM streams ORDER BY id").fetchall()
    by_id = {row["id"]: row for row in rows}

    for row in rows:
        stream_id = row["id"]
        parent_id = row["parent_stream_id"]
        if parent_id == stream_id:
            issues.append(f"stream {stream_id} is its own parent")
        elif parent_id is not None and parent_id not in by_id:
            issues.append(f"stream {stream_id} has missing parent {parent_id}")
        elif parent_id is not None and by_id[parent_id]["bundle_id"] != row["bundle_id"]:
            issues.append(f"stream {stream_id} parent {parent_id} belongs to another bundle")
        if row["status"] not in STREAM_STATUSES:
            issues.append(f"stream {stream_id} has invalid status {row['status']!r}")
        if row["priority"] is not None and (not isinstance(row["priority"], int) or row["priority"] < 0):
            issues.append(f"stream {stream_id} has invalid priority {row['priority']!r}")
        if not isinstance(row["revision"], int) or row["revision"] <= 0:
            issues.append(f"stream {stream_id} has invalid revision {row['revision']!r}")
        for column in ("owners", "tags"):
            issues.extend(_json_array_issues("stream", row, column))

    seen_cycles: set[frozenset[str]] = set()
    for start_id in by_id:
        path: list[str] = []
        positions: dict[str, int] = {}
        current_id: str | None = start_id
        while current_id in by_id:
            if current_id in positions:
                cycle = path[positions[current_id]:]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    issues.append(f"stream parent cycle: {' -> '.join(cycle + [current_id])}")
                break
            positions[current_id] = len(path)
            path.append(current_id)
            current_id = by_id[current_id]["parent_stream_id"]

    duplicates = connection.execute(
        "SELECT bundle_id, parent_stream_id, order_key, GROUP_CONCAT(id) AS ids "
        "FROM streams GROUP BY bundle_id, parent_stream_id, order_key HAVING COUNT(*) > 1 "
        "ORDER BY bundle_id, parent_stream_id, order_key"
    )
    for row in duplicates:
        issues.append(
            f"streams {row['bundle_id']} parent {_label(row['parent_stream_id'])} "
            f"share order_key {row['order_key']}: {row['ids']}"
        )
    return issues


def _check_comments(connection: sqlite3.Connection) -> list[str]:
    issues: list[str] = []
    stream_ids = {row[0] for row in connection.execute("SELECT id FROM streams")}
    for row in connection.execute("SELECT * FROM comments ORDER BY id"):
        if row["stream_id"] not in stream_ids:
            issues.append(f"comment {row['id']} has missing stream {row['stream_id']}")
        if row["sticky_note"] not in (0, 1):
            issues.append(f"comment {row['id']} has invalid sticky_note {row['sticky_note']!r}")
        if not isinstance(row["revision"], int) or row["revision"] <= 0:
            issues.append(f"comment {row['id']} has invalid revision {row['revision']!r}")
    return issues


def _check_history(connection: sqlite3.Connection) -> list[str]:
    issues: list[str] = []
    for row in connection.execute("SELECT * FROM history ORDER BY sequence"):
        if row["object_type"] not in {"bundle", "stream", "comment"}:
            issues.append(f"history {row['id']} has invalid object_type {row['object_type']!r}")
        try:
            changed_fields = json.loads(row["changed_fields"])
            if not isinstance(changed_fields, list):
                raise ValueError("not a list")
        except (TypeError, json.JSONDecodeError, ValueError) as error:
            issues.append(f"history {row['id']} has invalid changed_fields JSON: {error}")
        for column in ("before_value", "after_value"):
            if row[column] is not None:
                try:
                    json.loads(row[column])
                except json.JSONDecodeError as error:
                    issues.append(f"history {row['id']} has invalid {column} JSON: {error}")
    return issues


def _check_transactions(connection: sqlite3.Connection) -> list[str]:
    issues: list[str] = []
    transaction_ids = {row[0] for row in connection.execute("SELECT id FROM transactions")}
    for row in connection.execute("SELECT * FROM transactions ORDER BY id"):
        if row["target_transaction_id"] is not None and row["target_transaction_id"] not in transaction_ids:
            issues.append(f"transaction {row['id']} has missing target {row['target_transaction_id']}")
    history_transaction_ids = connection.execute(
        "SELECT DISTINCT transaction_id FROM history WHERE transaction_id IS NOT NULL"
    )
    for row in history_transaction_ids:
        if row[0] not in transaction_ids:
            issues.append(f"history references missing transaction {row[0]}")
    return issues


def audit_database(path: str | Path) -> list[str]:
    """Return deterministic human-readable violations without changing the database."""

    database_path = Path(path).expanduser().resolve()
    if not database_path.exists():
        return [f"database does not exist: {database_path}"]
    uri = f"file:{database_path.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        return [f"cannot open database read-only: {error}"]
    connection.row_factory = sqlite3.Row
    try:
        issues: list[str] = []
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        issues.extend(f"SQLite integrity_check: {row[0]}" for row in integrity if row[0] != "ok")
        for row in connection.execute("PRAGMA foreign_key_check"):
            issues.append(f"foreign-key violation in {row[0]} rowid {row[1]}: parent {row[3]}")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        missing_tables = sorted(TABLES - tables)
        if missing_tables:
            return [f"missing required table: {table}" for table in missing_tables]
        issues.extend(_check_streams(connection))
        issues.extend(_check_comments(connection))
        issues.extend(_check_history(connection))
        issues.extend(_check_transactions(connection))
        return issues
    except sqlite3.Error as error:
        return [f"audit query failed: {error}"]
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Stream SQLite data without modifying it.")
    parser.add_argument(
        "--database",
        default=os.getenv("STREAM_DATABASE_PATH", "data/stream.sqlite3"),
        help="SQLite database path (default: STREAM_DATABASE_PATH or data/stream.sqlite3)",
    )
    args = parser.parse_args(argv)
    issues = audit_database(args.database)
    if issues:
        print(f"FAILED: {len(issues)} issue(s) found in {Path(args.database).expanduser()}")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"OK: no integrity issues found in {Path(args.database).expanduser()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
