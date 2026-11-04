"""Offline checks for gbp-mcp's BearerAuth middleware.

No proxy, Google, or network calls: the proxy settings are dummies and the protected
route is a stub. Run from mcp/ with `python -m unittest test_auth`, or from the repo
root with `python -m unittest discover -s mcp`.
"""

import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("GBP_PROXY_URL", "http://127.0.0.1:9/unused")
os.environ.setdefault("GBP_PROXY_KEY", "test-proxy-key")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import server  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TOKEN = "test-token-0123456789"


async def protected(request):
    return JSONResponse({"reached": True})


def client() -> TestClient:
    app = Starlette(routes=[Route("/mcp", protected, methods=["GET", "POST"])])
    app.add_middleware(server.BearerAuth)
    return TestClient(app)


class HealthTests(unittest.TestCase):
    def test_health_paths_answer_without_token(self):
        for token in (None, TOKEN):
            with mock.patch.object(server, "MCP_TOKEN", token):
                for path in ("/health", "/healthz"):
                    r = client().get(path)
                    self.assertEqual(r.status_code, 200, (token, path))
                    self.assertEqual(r.json(), {"ok": True})

    def test_real_app_serves_health(self):
        with mock.patch.object(server, "MCP_TOKEN", None):
            r = TestClient(server.app).get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True})


class FailClosedTests(unittest.TestCase):
    def test_unset_token_returns_503(self):
        for token in (None, ""):
            with mock.patch.object(server, "MCP_TOKEN", token):
                r = client().get("/mcp", headers={"Authorization": "Bearer anything"})
                self.assertEqual(r.status_code, 503, token)
                self.assertEqual(r.json(), {"error": "server not configured"})

    def test_real_app_unset_token_returns_503(self):
        with mock.patch.object(server, "MCP_TOKEN", None):
            r = TestClient(server.app).post("/mcp", json={})
        self.assertEqual(r.status_code, 503)


class BearerTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(server, "MCP_TOKEN", TOKEN)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_header_is_401(self):
        r = client().get("/mcp")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"error": "unauthorized"})

    def test_wrong_token_is_401(self):
        for value in (f"Bearer {TOKEN}x", f"Bearer {TOKEN[:-1]}", TOKEN, f"bearer {TOKEN}", "Bearer "):
            r = client().get("/mcp", headers={"Authorization": value})
            self.assertEqual(r.status_code, 401, value)

    def test_non_ascii_header_is_401_not_500(self):
        r = client().get("/mcp", headers={"Authorization": "Bearer tést".encode("latin-1")})
        self.assertEqual(r.status_code, 401)

    def test_correct_token_reaches_route(self):
        r = client().get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"reached": True})

    def test_comparison_is_constant_time(self):
        with mock.patch.object(server.hmac, "compare_digest", wraps=server.hmac.compare_digest) as spy:
            client().get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
        spy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
