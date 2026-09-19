import unittest
import tempfile
from pathlib import Path

from app import create_app
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


if __name__ == "__main__":
    unittest.main()
