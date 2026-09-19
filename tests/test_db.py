import tempfile
import unittest
from pathlib import Path

from app.db import Database
from app.repositories import NotFound, Repository, RevisionConflict


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "stream.sqlite3")
        self.database.migrate()
        self.repository = Repository(self.database)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_migration_enables_wal_and_foreign_keys(self) -> None:
        with self.database.read() as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)

    def test_stream_update_records_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice", priority=1)

        updated = self.repository.update_stream(
            stream["id"], stream["revision"], "alice", {"summary": "Prepare first release", "priority": 0}
        )

        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["summary"], "Prepare first release")
        history = self.repository.list_history("stream", stream["id"])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["actor"], "alice")
        self.assertEqual(history[-1]["changed_fields"], ["priority", "revision", "summary"])

    def test_stale_stream_update_returns_current_value(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        self.repository.update_stream(stream["id"], 1, "alice", {"summary": "New value"})

        with self.assertRaises(RevisionConflict) as context:
            self.repository.update_stream(stream["id"], 1, "bob", {"summary": "Stale value"})

        self.assertEqual(context.exception.current["summary"], "New value")
        self.assertEqual(context.exception.current["revision"], 2)

    def test_comments_are_independently_revisioned_and_append_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        comment = self.repository.add_comment(stream["id"], "Left off at packaging", "alice")

        updated = self.repository.update_comment(comment["id"], 1, "bob", "Packaging is complete")

        self.assertEqual(updated["revision"], 2)
        self.assertEqual(self.repository.get_stream(stream["id"])["revision"], 1)
        self.assertEqual(len(self.repository.list_history("comment", comment["id"])), 2)

    def test_child_stream_must_belong_to_same_bundle(self) -> None:
        first = self.repository.create_bundle("First", "alice")
        second = self.repository.create_bundle("Second", "alice")
        parent = self.repository.create_stream(first["id"], "Parent", "alice")

        with self.assertRaises(NotFound):
            self.repository.create_stream(second["id"], "Child", "alice", parent_stream_id=parent["id"])

    def test_stream_cannot_become_its_own_ancestor(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        parent = self.repository.create_stream(bundle["id"], "Parent", "alice")
        child = self.repository.create_stream(bundle["id"], "Child", "alice", parent_stream_id=parent["id"])

        with self.assertRaises(ValueError):
            self.repository.update_stream(
                parent["id"], parent["revision"], "alice", {"parent_stream_id": child["id"]}
            )


if __name__ == "__main__":
    unittest.main()
