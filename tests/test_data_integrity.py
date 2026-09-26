import tempfile
import unittest
from pathlib import Path

from app.data_integrity import audit_database
from app.db import Database
from app.repositories import Repository


class DataIntegrityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "stream.sqlite3"
        self.database = Database(self.path)
        self.database.migrate()
        self.repository = Repository(self.database)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_clean_database_passes(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        self.repository.create_stream(bundle["id"], "First", "alice")
        self.assertEqual(audit_database(self.path), [])

    def test_audit_reports_tree_and_payload_corruption(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        first = self.repository.create_stream(bundle["id"], "First", "alice")
        second = self.repository.create_stream(bundle["id"], "Second", "alice")
        third = self.repository.create_stream(bundle["id"], "Third", "alice")
        fourth = self.repository.create_stream(bundle["id"], "Fourth", "alice")
        with self.database.transaction() as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "UPDATE streams SET parent_stream_id = ?, owners = ?, order_key = ? WHERE id = ?",
                (first["id"], "not-json", 1000, second["id"]),
            )
            connection.execute(
                "UPDATE streams SET parent_stream_id = ? WHERE id = ?",
                (second["id"], first["id"]),
            )
            connection.execute(
                "UPDATE streams SET order_key = ? WHERE id = ?",
                (1000, third["id"]),
            )
            connection.execute(
                "UPDATE streams SET order_key = ? WHERE id = ?",
                (1000, fourth["id"]),
            )
            connection.execute("PRAGMA foreign_keys = ON")

        issues = audit_database(self.path)
        self.assertTrue(any("stream parent cycle" in issue for issue in issues))
        self.assertTrue(any("invalid owners JSON" in issue for issue in issues))
        self.assertTrue(any("share order_key" in issue for issue in issues))

    def test_audit_reports_cross_bundle_parent_and_bad_history_json(self) -> None:
        first_bundle = self.repository.create_bundle("First", "alice")
        second_bundle = self.repository.create_bundle("Second", "alice")
        parent = self.repository.create_stream(first_bundle["id"], "Parent", "alice")
        child = self.repository.create_stream(second_bundle["id"], "Child", "alice")
        with self.database.transaction() as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "UPDATE streams SET parent_stream_id = ? WHERE id = ?",
                (parent["id"], child["id"]),
            )
            connection.execute(
                "INSERT INTO history(id, object_type, object_id, actor, changed_at, changed_fields) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("bad-history", "stream", child["id"], "tester", "now", "not-json"),
            )
            connection.execute("PRAGMA foreign_keys = ON")

        issues = audit_database(self.path)
        self.assertTrue(any("belongs to another bundle" in issue for issue in issues))
        self.assertTrue(any("invalid changed_fields JSON" in issue for issue in issues))
