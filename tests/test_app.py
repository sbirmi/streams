import unittest

from app import create_app
from app.config import Settings


class ApplicationShellTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(Settings(app_name="Test Stream", environment="test"))
        self.client = self.app.test_client()

    def test_home_page_renders_application_shell(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Stream", response.data)
        self.assertIn(b"Your streams will appear here", response.data)

    def test_health_endpoint_returns_ok_and_request_id(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertTrue(response.headers["X-Request-ID"])


if __name__ == "__main__":
    unittest.main()

