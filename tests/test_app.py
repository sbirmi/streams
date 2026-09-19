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
        self.assertIn(b"Test Stream", response.data)
        self.assertIn(b"Loading streams", response.data)

    def test_health_endpoint_returns_ok_and_request_id(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertTrue(response.headers["X-Request-ID"])

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

    def test_shortcuts_endpoint_returns_complete_configured_map(self) -> None:
        response = self.client.get("/api/shortcuts")

        self.assertEqual(response.status_code, 200)
        shortcuts = response.json["shortcuts"]
        self.assertEqual(shortcuts["insert_before"], ["ip"])
        self.assertEqual(shortcuts["delete_stream"], ["ds"])
        self.assertEqual(shortcuts["zoom_back"], ["Z Backspace"])
        self.assertEqual(shortcuts["move_down"], ["j", "ArrowDown"])

    def test_shortcut_config_requires_every_action_and_rejects_legacy_map(self) -> None:
        path = Path(self.tempdir.name) / "shortcuts.yaml"
        path.write_text("insert_before: i\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            load_shortcuts(str(path))

    def test_shortcut_config_supports_alias_lists_and_named_sequences(self) -> None:
        path = Path(self.tempdir.name) / "shortcuts.yaml"
        path.write_text("\n".join([
            "move_left: [h, ArrowLeft]", "move_right: l", "move_up: k", "move_down: j",
            "edit: e", "add_comment: a", "open_help: ?", "cancel_command: Escape",
            "zoom_enter: Z Enter", "zoom_back: Z Backspace", "delete_stream: ds",
            "delete_comment: dc", "insert_before: ip", "insert_after: in", "insert_child: ic",
            "fold_open: zo", "fold_open_all: zO", "fold_close: zc", "fold_close_all: zC",
            "fold_toggle: za",
        ]) + "\n", encoding="utf-8")

        shortcuts = load_shortcuts(str(path))
        self.assertEqual(shortcuts["move_left"], ["h", "ArrowLeft"])
        self.assertEqual(shortcuts["zoom_enter"], ["Z Enter"])

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
