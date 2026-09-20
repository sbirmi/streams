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
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 4)

    def test_stream_favorite_defaults_false_and_updates_with_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")

        self.assertIs(stream["favorite"], False)
        updated = self.repository.update_stream(
            stream["id"], stream["revision"], "alice", {"favorite": True}
        )

        self.assertIs(updated["favorite"], True)
        self.assertEqual(updated["revision"], 2)
        self.assertIn("updated_at", updated)
        history = self.repository.list_history("stream", stream["id"])
        self.assertEqual(history[-1]["changed_fields"], ["favorite", "revision"])

    def test_stream_favorite_requires_boolean(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")

        with self.assertRaises(ValueError):
            self.repository.update_stream(stream["id"], stream["revision"], "alice", {"favorite": 1})

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

    def test_stream_delete_promotes_children_and_records_audit_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        parent = self.repository.create_stream(bundle["id"], "Parent", "alice")
        child = self.repository.create_stream(bundle["id"], "Child", "alice", parent_stream_id=parent["id"])
        comment = self.repository.add_comment(parent["id"], "Keep the context", "alice")

        deleted = self.repository.delete_stream(parent["id"], parent["revision"], "bob")

        self.assertEqual(deleted["id"], parent["id"])
        self.assertEqual(self.repository.get_stream(child["id"])["parent_stream_id"], None)
        with self.assertRaises(NotFound):
            self.repository.get_stream(parent["id"])
        with self.assertRaises(NotFound):
            self.repository.get_comment(comment["id"])
        self.assertIsNone(self.repository.list_history("stream", parent["id"])[-1]["after_value"])
        self.assertIsNone(self.repository.list_history("comment", comment["id"])[-1]["after_value"])
        self.assertEqual(self.repository.get_stream(child["id"])["revision"], 2)

    def test_stream_delete_keeps_promoted_children_in_deleted_root_slot(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        before = self.repository.create_stream(bundle["id"], "Before", "alice")
        parent = self.repository.create_stream(bundle["id"], "Parent", "alice")
        after = self.repository.create_stream(bundle["id"], "After", "alice")
        first_child = self.repository.create_stream(bundle["id"], "First child", "alice", parent_stream_id=parent["id"])
        second_child = self.repository.create_stream(bundle["id"], "Second child", "alice", parent_stream_id=parent["id"])

        self.repository.delete_stream(parent["id"], parent["revision"], "bob")

        streams = self.repository.list_streams(bundle["id"])
        self.assertEqual(
            [stream["id"] for stream in streams],
            [before["id"], first_child["id"], second_child["id"], after["id"]],
        )
        self.assertEqual(
            [stream["order_key"] for stream in streams],
            [1000, 2000, 3000, 4000],
        )

    def test_stale_stream_delete_returns_current_value(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        self.repository.update_stream(stream["id"], 1, "alice", {"summary": "New value"})

        with self.assertRaises(RevisionConflict) as context:
            self.repository.delete_stream(stream["id"], 1, "bob")

        self.assertEqual(context.exception.current["summary"], "New value")
        self.assertEqual(self.repository.get_stream(stream["id"])["revision"], 2)

    def test_comments_are_independently_revisioned_and_append_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        comment = self.repository.add_comment(stream["id"], "Left off at packaging", "alice")

        updated = self.repository.update_comment(comment["id"], 1, "bob", "Packaging is complete")

        self.assertEqual(updated["revision"], 2)
        self.assertEqual(self.repository.get_stream(stream["id"])["revision"], 1)
        self.assertEqual(len(self.repository.list_history("comment", comment["id"])), 2)

    def test_comments_are_listed_newest_first_with_deterministic_ties(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        older = self.repository.add_comment(stream["id"], "First update", "alice", comment_id="comment-1")
        newest = self.repository.add_comment(stream["id"], "Second update", "bob", comment_id="comment-2")
        tied = self.repository.add_comment(stream["id"], "Same-second update", "carol", comment_id="comment-3")

        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE comments SET created_at = CASE id "
                "WHEN ? THEN ? WHEN ? THEN ? WHEN ? THEN ? END "
                "WHERE id IN (?, ?, ?)",
                (
                    older["id"], "2026-01-01T00:00:00Z",
                    newest["id"], "2026-01-01T00:00:01Z",
                    tied["id"], "2026-01-01T00:00:01Z",
                    older["id"], newest["id"], tied["id"],
                ),
            )

        comments = self.repository.list_comments(stream["id"])
        self.assertEqual([comment["id"] for comment in comments], [tied["id"], newest["id"], older["id"]])

    def test_comment_delete_requires_current_revision_and_records_history(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(bundle["id"], "Prepare release", "alice")
        comment = self.repository.add_comment(stream["id"], "Left off at packaging", "alice")
        self.repository.update_comment(comment["id"], 1, "alice", "Packaging is complete")

        with self.assertRaises(RevisionConflict):
            self.repository.delete_comment(comment["id"], 1, "bob")
        self.repository.delete_comment(comment["id"], 2, "bob")

        with self.assertRaises(NotFound):
            self.repository.get_comment(comment["id"])
        self.assertIsNone(self.repository.list_history("comment", comment["id"])[-1]["after_value"])

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

    def test_stream_insertion_preserves_sibling_order(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        first = self.repository.create_stream(bundle["id"], "First", "alice")
        last = self.repository.create_stream(bundle["id"], "Last", "alice")
        middle = self.repository.create_stream(
            bundle["id"], "Middle", "alice", anchor_stream_id=last["id"], placement="before"
        )

        streams = self.repository.list_streams(bundle["id"])
        self.assertEqual([stream["id"] for stream in streams], [first["id"], middle["id"], last["id"]])
        self.assertEqual([stream["order_key"] for stream in streams], [1000, 1500, 2000])

    def test_move_stream_before_after_child_and_promote(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        first = self.repository.create_stream(bundle["id"], "First", "alice")
        second = self.repository.create_stream(bundle["id"], "Second", "alice")
        third = self.repository.create_stream(bundle["id"], "Third", "alice")
        parent = self.repository.create_stream(bundle["id"], "Parent", "alice")

        moved = self.repository.move_streams(
            [third["id"]], {third["id"]: third["revision"]}, first["id"], "before", "bob"
        )[0]
        self.assertEqual(moved["parent_stream_id"], None)
        self.assertEqual([item["id"] for item in self.repository.list_streams(bundle["id"])],
                         [third["id"], first["id"], second["id"], parent["id"]])

        moved = self.repository.move_streams(
            [second["id"]], {second["id"]: self.repository.get_stream(second["id"])["revision"]}, parent["id"], "child", "bob"
        )[0]
        self.assertEqual(moved["parent_stream_id"], parent["id"])
        promoted = self.repository.move_streams(
            [second["id"]], {second["id"]: moved["revision"]}, parent["id"], "after", "bob"
        )[0]
        self.assertIsNone(promoted["parent_stream_id"])

    def test_move_streams_requires_contiguous_siblings_and_current_revisions(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        first = self.repository.create_stream(bundle["id"], "First", "alice")
        second = self.repository.create_stream(bundle["id"], "Second", "alice")
        third = self.repository.create_stream(bundle["id"], "Third", "alice")
        with self.assertRaises(ValueError):
            self.repository.move_streams(
                [first["id"], third["id"]],
                {first["id"]: first["revision"], third["id"]: third["revision"]},
                second["id"], "after", "bob"
            )
        with self.assertRaises(RevisionConflict):
            self.repository.move_streams(
                [first["id"]], {first["id"]: 0}, third["id"], "after", "bob"
            )

    def test_move_streams_rejects_descendant_target(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        parent = self.repository.create_stream(bundle["id"], "Parent", "alice")
        child = self.repository.create_stream(bundle["id"], "Child", "alice", parent_stream_id=parent["id"])
        with self.assertRaises(ValueError):
            self.repository.move_streams(
                [parent["id"]], {parent["id"]: parent["revision"]}, child["id"], "child", "bob"
            )

    def test_order_key_is_server_controlled(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        stream = self.repository.create_stream(bundle["id"], "First", "alice")
        with self.assertRaises(ValueError):
            self.repository.update_stream(stream["id"], stream["revision"], "alice", {"order_key": 5})

    def test_rooted_view_context_rejects_sibling_insertion_at_root(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        root = self.repository.create_stream(bundle["id"], "Work", "alice")

        with self.assertRaises(ValueError):
            self.repository.create_stream(
                bundle["id"], "Sibling", "alice", anchor_stream_id=root["id"],
                placement="before", root_stream_id=root["id"],
            )

    def test_rooted_view_context_allows_child_and_descendant_sibling_insertion(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        root = self.repository.create_stream(bundle["id"], "Work", "alice")
        child = self.repository.create_stream(bundle["id"], "Task", "alice", parent_stream_id=root["id"])

        sibling = self.repository.create_stream(
            bundle["id"], "Next task", "alice", parent_stream_id=root["id"], anchor_stream_id=child["id"],
            placement="after", root_stream_id=root["id"],
        )
        self.assertEqual(sibling["parent_stream_id"], root["id"])

    def test_stream_priority_can_be_empty(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        stream = self.repository.create_stream(bundle["id"], "Unprioritized", "alice", priority=None)

        self.assertIsNone(stream["priority"])

    def test_stream_owners_and_deadline_are_normalized_and_persisted(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        stream = self.repository.create_stream(
            bundle["id"], "Plan release", "alice",
            owners=[" alice ", "", "bob", "  "], deadline="2026-10-05",
        )

        self.assertEqual(stream["owners"], ["alice", "bob"])
        self.assertEqual(stream["deadline"], "2026-10-05")
        updated = self.repository.update_stream(
            stream["id"], stream["revision"], "alice",
            {"owners": ["carol", "", " dave "], "deadline": ""},
        )
        self.assertEqual(updated["owners"], ["carol", "dave"])
        self.assertIsNone(updated["deadline"])

    def test_stream_tags_are_normalized_and_ordered(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        stream = self.repository.create_stream(
            bundle["id"], "Tagged", "alice", tags=[" work ", "", "urgent", "  "]
        )
        self.assertEqual(stream["tags"], ["work", "urgent"])

        updated = self.repository.update_stream(
            stream["id"], stream["revision"], "alice", {"tags": ["later", "", "review"]}
        )
        self.assertEqual(updated["tags"], ["later", "review"])

    def test_stream_tags_must_be_strings(self) -> None:
        bundle = self.repository.create_bundle("Todos", "alice")
        with self.assertRaises(ValueError):
            self.repository.create_stream(bundle["id"], "Tagged", "alice", tags=["valid", 2])

    def test_stream_deadline_must_be_date_only(self) -> None:
        bundle = self.repository.create_bundle("Index", "alice")
        with self.assertRaises(ValueError):
            self.repository.create_stream(bundle["id"], "Plan release", "alice", deadline="tomorrow")


if __name__ == "__main__":
    unittest.main()
