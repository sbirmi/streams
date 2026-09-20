import unittest
import tempfile
from pathlib import Path

from app import create_app, load_shortcuts
from app.config import Settings


class ApplicationShellTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        database_path = str(Path(self.tempdir.name) / "test.sqlite3")
        self.app = create_app(Settings(app_name="Test Stream", environment="test", database_path=database_path))
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_home_page_renders_application_shell(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<title>streams: Index</title>", response.data)
        self.assertIn(b"Test Stream", response.data)
        self.assertIn(b"Loading streams", response.data)
        self.assertIn(b'data-action="copy-link"', response.data)
        self.assertIn(b'value="manual">Manual order', response.data)

    def test_health_endpoint_returns_ok_and_request_id(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertTrue(response.headers["X-Request-ID"])

    def test_dashboard_route_renders_application_shell(self) -> None:
        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<title>streams: Dashboard</title>", response.data)
        self.assertIn(b"data-action=\"dashboard\"", response.data)

    def test_stream_api_create_read_and_conflict(self) -> None:
        bundle_response = self.client.post(
            "/api/bundles", json={"name": "Todos", "actor": "alice"}
        )
        self.assertEqual(bundle_response.status_code, 201)
        bundle = bundle_response.json["bundle"]

        stream_response = self.client.post(
            f"/api/bundles/{bundle['id']}/streams",
            json={"summary": "Prepare release", "actor": "alice"},
        )
        self.assertEqual(stream_response.status_code, 201)
        stream = stream_response.json["stream"]
        self.assertIs(stream["favorite"], False)

        update_response = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": 1, "actor": "alice", "changes": {"summary": "Ship release"}},
        )
        self.assertEqual(update_response.status_code, 200)

        conflict_response = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": 1, "actor": "bob", "changes": {"summary": "Stale edit"}},
        )
        self.assertEqual(conflict_response.status_code, 409)
        self.assertEqual(conflict_response.json["current"]["summary"], "Ship release")

    def test_stream_api_updates_favorite_with_revision_check(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Prepare release", "actor": "alice"}
        ).json["stream"]

        updated = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": stream["revision"], "actor": "alice", "changes": {"favorite": True}},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertIs(updated.json["stream"]["favorite"], True)
        self.assertEqual(updated.json["stream"]["revision"], 2)

        conflict = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": stream["revision"], "actor": "bob", "changes": {"favorite": False}},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertIs(conflict.json["current"]["favorite"], True)

    def test_stream_status_api_supports_single_and_bulk_updates(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        first = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "First", "actor": "alice"}).json["stream"]
        second = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "Second", "actor": "alice"}).json["stream"]

        response = self.client.post("/api/streams/status", json={
            "actor": "alice", "stream_ids": [first["id"], second["id"]],
            "revisions": {first["id"]: 1, second["id"]: 1}, "status": "no_action",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["status"] for item in response.json["streams"]], ["no_action", "no_action"])

    def test_move_api_moves_a_stream_with_revision_check(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        first = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "First", "actor": "alice"}).json["stream"]
        second = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "Second", "actor": "alice"}).json["stream"]
        response = self.client.post("/api/streams/move", json={
            "stream_ids": [second["id"]], "revisions": {second["id"]: second["revision"]},
            "target_stream_id": first["id"], "placement": "before", "actor": "bob",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["streams"][0]["id"], second["id"])
        stale = self.client.post("/api/streams/move", json={
            "stream_ids": [second["id"]], "revisions": {second["id"]: second["revision"]},
            "target_stream_id": first["id"], "placement": "after", "actor": "bob",
        })
        self.assertEqual(stale.status_code, 409)

    def test_stream_api_persists_owners_and_deadline_on_create_and_update(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams",
            json={"summary": "Prepare release", "actor": "alice", "owners": [" alice ", "", "bob"], "deadline": "2026-10-05"},
        ).json["stream"]
        self.assertEqual(stream["owners"], ["alice", "bob"])
        self.assertEqual(stream["deadline"], "2026-10-05")
        updated = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": stream["revision"], "actor": "alice", "changes": {"owners": ["carol"], "deadline": None}},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["stream"]["owners"], ["carol"])
        self.assertIsNone(updated.json["stream"]["deadline"])

    def test_stream_api_persists_normalized_tags_on_create_and_update(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams",
            json={"summary": "Prepare release", "actor": "alice", "tags": [" work ", "", "urgent"]},
        ).json["stream"]
        self.assertEqual(stream["tags"], ["work", "urgent"])
        updated = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": stream["revision"], "actor": "alice", "changes": {"tags": ["later", "", "review"]}},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["stream"]["tags"], ["later", "review"])

    def test_delete_api_uses_revision_preconditions_for_streams_and_comments(self) -> None:
        bundle_response = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"})
        bundle = bundle_response.json["bundle"]
        stream_response = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Prepare release", "actor": "alice"}
        )
        stream = stream_response.json["stream"]
        comment_response = self.client.post(
            f"/api/streams/{stream['id']}/comments", json={"body": "Packaging", "actor": "alice"}
        )
        comment = comment_response.json["comment"]

        stale_stream = self.client.delete(
            f"/api/streams/{stream['id']}", json={"revision": 0, "actor": "bob"}
        )
        self.assertEqual(stale_stream.status_code, 409)
        self.assertEqual(stale_stream.json["current"]["id"], stream["id"])

        delete_comment = self.client.delete(
            f"/api/comments/{comment['id']}", json={"revision": comment["revision"], "actor": "bob"}
        )
        self.assertEqual(delete_comment.status_code, 200)
        delete_stream = self.client.delete(
            f"/api/streams/{stream['id']}", json={"revision": stream["revision"], "actor": "bob"}
        )
        self.assertEqual(delete_stream.status_code, 200)

    def test_comment_update_api_uses_revision_preconditions(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Prepare release", "actor": "alice"}
        ).json["stream"]
        comment = self.client.post(
            f"/api/streams/{stream['id']}/comments", json={"body": "Packaging", "actor": "alice"}
        ).json["comment"]
        updated = self.client.patch(
            f"/api/comments/{comment['id']}",
            json={"revision": comment["revision"], "actor": "bob", "body": "Packaging is complete"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["comment"]["revision"], 2)
        conflict = self.client.patch(
            f"/api/comments/{comment['id']}",
            json={"revision": comment["revision"], "actor": "carol", "body": "Stale edit"},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json["current"]["body"], "Packaging is complete")

    def test_shortcuts_endpoint_returns_complete_configured_map(self) -> None:
        response = self.client.get("/api/shortcuts")

        self.assertEqual(response.status_code, 200)
        shortcuts = response.json["shortcuts"]
        self.assertEqual(shortcuts["insert_before"], ["ip"])
        self.assertEqual(shortcuts["delete_stream"], ["ds"])
        self.assertEqual(shortcuts["zoom_back"], ["Z Backspace"])
        self.assertEqual(shortcuts["move_down"], ["j", "ArrowDown"])
        self.assertEqual(shortcuts["move_previous_sibling"], ["("])
        self.assertEqual(shortcuts["move_next_sibling"], [")"])
        self.assertEqual(shortcuts["transaction_undo"], ["tu"])
        self.assertEqual(shortcuts["transaction_redo"], ["tr"])

    def test_delete_block_api_deletes_selected_subtree(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        first = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "First", "actor": "alice"}).json["stream"]
        child = self.client.post(f"/api/bundles/{bundle['id']}/streams", json={"summary": "Child", "actor": "alice", "parent_stream_id": first["id"]}).json["stream"]
        response = self.client.post("/api/streams/delete-block", json={
            "stream_ids": [first["id"]], "revisions": {first["id"]: first["revision"], child["id"]: child["revision"]}, "actor": "bob",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json["deleted_stream_ids"]), {first["id"], child["id"]})

    def test_shortcut_config_requires_every_action_and_rejects_legacy_map(self) -> None:
        path = Path(self.tempdir.name) / "shortcuts.yaml"
        path.write_text("insert_before: i\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            load_shortcuts(str(path))

    def test_shortcut_config_supports_alias_lists_and_named_sequences(self) -> None:
        path = Path(self.tempdir.name) / "shortcuts.yaml"
        path.write_text("\n".join([
            "move_left: [h, ArrowLeft]", "move_right: l", "move_up: k", "move_down: j",
            "move_previous_sibling: (", "move_next_sibling: )",
            "edit: e", "add_comment: a", "open_help: ?", "cancel_command: Escape",
            "zoom_enter: Z Enter", "zoom_back: Z Backspace", "delete_stream: ds",
            "delete_comment: dc", "insert_before: ip", "insert_after: in", "insert_child: ic",
            "delete_visual: dv",
            "fold_open: zo", "fold_open_all: zO", "fold_close: zc", "fold_close_all: zC",
            "fold_toggle: za", "start_move: m", "start_selection: v", "move_before: p",
            "move_after: n", "move_child: c", "move_promote: u", "mark_open: so",
            "mark_resolved: sr", "mark_no_action: sn",
            "transaction_undo: tu", "transaction_redo: tr",
        ]) + "\n", encoding="utf-8")

        shortcuts = load_shortcuts(str(path))
        self.assertEqual(shortcuts["move_left"], ["h", "ArrowLeft"])
        self.assertEqual(shortcuts["zoom_enter"], ["Z Enter"])

    def test_transaction_routes_undo_redo_and_list_history(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Draft", "actor": "alice"}
        ).json["stream"]
        updated = self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"actor": "bob", "revision": stream["revision"], "changes": {"summary": "Final"}},
        )
        self.assertEqual(updated.status_code, 200)

        response = self.client.post("/api/transactions/undo", json={"actor": "carol"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["transaction"]["kind"], "undo")
        self.assertEqual(response.json["transaction"]["original_transaction"]["actor"], "bob")
        self.assertEqual(response.json["focus"]["stream_id"], stream["id"])

        response = self.client.post("/api/transactions/redo", json={"actor": "carol"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["transaction"]["kind"], "redo")

        response = self.client.get("/api/transactions")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json["transactions"]), 4)

    def test_transaction_state_endpoint_reports_logical_position(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Draft", "actor": "alice"}
        ).json["stream"]
        self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"actor": "bob", "revision": stream["revision"], "changes": {"summary": "Final"}},
        )

        response = self.client.get("/api/transactions/state")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["state"]["at_head"])
        self.assertEqual(response.json["state"]["mode"], "head")
        self.assertEqual(response.json["state"]["transaction"]["actor"], "bob")

        self.client.post("/api/transactions/undo", json={"actor": "carol"})
        response = self.client.get("/api/transactions/state")
        self.assertFalse(response.json["state"]["at_head"])
        self.assertEqual(response.json["state"]["mode"], "historical")
        self.assertEqual(response.json["state"]["transaction"]["actor"], "bob")

        self.client.post("/api/transactions/redo", json={"actor": "carol"})
        response = self.client.get("/api/transactions/state")
        self.assertTrue(response.json["state"]["at_head"])

        self.client.post("/api/transactions/undo", json={"actor": "carol"})
        current = self.client.get(f"/api/streams/{stream['id']}").json["stream"]
        self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"actor": "dana", "revision": current["revision"], "changes": {"summary": "Different"}},
        )
        response = self.client.get("/api/transactions/state")
        self.assertTrue(response.json["state"]["at_head"])
        self.assertEqual(response.json["state"]["transaction"]["actor"], "dana")

    def test_transaction_explorer_filters_and_detail_include_history_metadata(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        stream = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Release notes", "actor": "alice"}
        ).json["stream"]
        self.client.patch(
            f"/api/streams/{stream['id']}",
            json={"revision": stream["revision"], "actor": "bob", "changes": {"summary": "Release checklist"}},
        )

        response = self.client.get("/api/transactions?q=updated&kind=mutation&state=active&limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["transactions"]), 1)
        transaction = response.json["transactions"][0]
        self.assertEqual(transaction["actor"], "bob")

        detail = self.client.get(f"/api/transactions/{transaction['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["transaction"]["history"][0]["object_id"], stream["id"])
        self.assertEqual(detail.json["transaction"]["related_objects"][0]["summary"], "Release checklist")

        page = self.client.get("/transactions?q=updated")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"<title>streams: Transactions</title>", page.data)
        self.assertIn(b"Transaction history", page.data)
        self.assertIn(b"transaction-query", page.data)
        self.assertIn(b"transactions.js", page.data)

    def test_api_root_context_rejects_sibling_of_rooted_view(self) -> None:
        bundle = self.client.post("/api/bundles", json={"name": "Todos", "actor": "alice"}).json["bundle"]
        root = self.client.post(
            f"/api/bundles/{bundle['id']}/streams", json={"summary": "Work", "actor": "alice"}
        ).json["stream"]

        response = self.client.post(
            f"/api/bundles/{bundle['id']}/streams",
            json={"summary": "Sibling", "actor": "alice", "anchor_stream_id": root["id"],
                  "placement": "before", "root_stream_id": root["id"]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rooted view", response.json["message"])


if __name__ == "__main__":
    unittest.main()
