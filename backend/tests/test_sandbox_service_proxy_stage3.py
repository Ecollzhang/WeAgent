import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from app.sandbox.api import routes
from app.sandbox.host.client import OrchestratorClient


class _FakeResponse:
    def __init__(self, status=200, headers=None, body=b"ok"):
        self.status = status
        self.headers = headers or {}
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeOpener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, req, timeout=None):
        self.requests.append((req, timeout))
        return self.response


class FakeSandboxProxyManager:
    def __init__(self):
        self.calls = []

    def proxy_service(self, session_id, service_id, path, method, headers, body, query_string):
        self.calls.append((session_id, service_id, path, method, headers, body, query_string))
        return {
            "status_code": 201,
            "headers": [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Location", "http://localhost:1234/api/services/svc_1/proxy/next?ok=1"),
                ("Transfer-Encoding", "chunked"),
            ],
            "body": b"<h1>proxied</h1>",
        }

    def validate_service_token(self, session_id, service_id, token):
        return session_id == "s1" and service_id == "svc_1" and token == "preview-token"


class SandboxServiceProxyStage3Test(unittest.TestCase):
    def test_host_proxy_route_forwards_request_and_rewrites_location(self):
        fake = FakeSandboxProxyManager()
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()

        response = client.post(
            "/api/sandbox/sessions/s1/services/svc_1/proxy/assets/app.js?v=1&token=preview-token",
            data=b"payload",
            headers={"X-Test": "yes"},
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(b"<h1>proxied</h1>", response.data)
        self.assertEqual("text/html; charset=utf-8", response.headers["Content-Type"])
        self.assertEqual(["text/html; charset=utf-8"], response.headers.getlist("Content-Type"))
        self.assertEqual(
            "/api/sandbox/sessions/s1/services/svc_1/proxy/next?ok=1",
            response.headers["Location"],
        )
        self.assertEqual(
            ("s1", "svc_1", "assets/app.js", "POST", unittest.mock.ANY, b"payload", "v=1"),
            fake.calls[0],
        )
        self.assertIn("weagent_preview_token=preview-token", response.headers["Set-Cookie"])
        routes._manager = None

    def test_host_proxy_rewrites_absolute_asset_paths(self):
        fake = FakeSandboxProxyManager()
        fake.proxy_service = lambda *args, **kwargs: {
            "status_code": 200,
            "headers": [("Content-Type", "text/html; charset=utf-8")],
            "body": (
                b'<script type="module" src="/src/main.js"></script>'
                b'<link href="/assets/app.css" rel="stylesheet">'
                b'<form action="/api/login"></form>'
                b'<style>.logo{background:url("/static/logo.png")}</style>'
                b'<script>import "/@vite/client"; const p="/_next/static/chunk.js"</script>'
            ),
        }
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()

        response = client.get(
            "/api/sandbox/sessions/s1/services/svc_1/proxy/?token=preview-token"
        )
        html = response.data.decode("utf-8")
        prefix = "/api/sandbox/sessions/s1/services/svc_1/proxy/"

        self.assertIn(f'src="{prefix}src/main.js"', html)
        self.assertIn(f'href="{prefix}assets/app.css"', html)
        self.assertIn(f'action="{prefix}api/login"', html)
        self.assertIn(f'url("{prefix}static/logo.png")', html)
        self.assertIn(f'import "{prefix}@vite/client"', html)
        self.assertIn(f'const p="{prefix}_next/static/chunk.js"', html)
        routes._manager = None

    def test_host_proxy_rewrites_css_paths_and_drops_content_encoding(self):
        fake = FakeSandboxProxyManager()
        fake.proxy_service = lambda *args, **kwargs: {
            "status_code": 200,
            "headers": [
                ("Content-Type", "text/css; charset=utf-8"),
                ("Content-Encoding", "gzip"),
            ],
            "body": (
                b'@import "/assets/theme.css";'
                b'.hero{background:url("/assets/bg.png")}'
            ),
        }
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()

        response = client.get(
            "/api/sandbox/sessions/s1/services/svc_1/proxy/assets/app.css?token=preview-token"
        )
        css = response.data.decode("utf-8")
        prefix = "/api/sandbox/sessions/s1/services/svc_1/proxy/"

        self.assertEqual("text/css; charset=utf-8", response.headers["Content-Type"])
        self.assertEqual(["text/css; charset=utf-8"], response.headers.getlist("Content-Type"))
        self.assertIn(f'@import "{prefix}assets/theme.css"', css)
        self.assertIn(f'url("{prefix}assets/bg.png")', css)
        self.assertNotIn("Content-Encoding", response.headers)
        routes._manager = None

    def test_orchestrator_client_proxies_to_container_service_endpoint(self):
        client = OrchestratorClient("localhost", 1234)
        opener = _FakeOpener(_FakeResponse(
            status=207,
            headers={"Content-Type": "application/json"},
            body=b'{"ok":true}',
        ))

        with patch("app.sandbox.host.client.urllib.request.build_opener", return_value=opener):
            result = client.proxy_service(
                service_id="svc 1",
                path="assets/app.js",
                method="POST",
                headers={"Host": "bad.local", "X-Test": "yes", "Accept-Encoding": "gzip, br"},
                body=b"{}",
                query_string="v=1",
            )

        req, timeout = opener.requests[0]
        self.assertEqual("http://localhost:1234/api/services/svc%201/proxy/assets/app.js?v=1", req.full_url)
        self.assertEqual("POST", req.get_method())
        self.assertEqual(b"{}", req.data)
        self.assertEqual("yes", req.headers["X-test"])
        self.assertNotIn("Host", req.headers)
        self.assertNotIn("Accept-encoding", req.headers)
        self.assertEqual(60, timeout)
        self.assertEqual(207, result["status_code"])
        self.assertEqual(b'{"ok":true}', result["body"])

    def test_container_proxy_routes_to_local_service_and_rewrites_location(self):
        server = self._import_container_server()
        opener = _FakeOpener(_FakeResponse(
            status=302,
            headers={
                "Location": "http://localhost:5173/login?back=1",
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
            },
            body=b"redirect",
        ))

        with patch.object(server.urllib.request, "build_opener", return_value=opener):
            response = server.app.test_client().get(
                "/api/services/svc_1/proxy/assets/app.css?v=1",
                headers={"Accept-Encoding": "gzip, br"},
            )

        req, timeout = opener.requests[0]
        self.assertEqual("http://127.0.0.1:5173/assets/app.css?v=1", req.full_url)
        self.assertEqual("GET", req.get_method())
        self.assertNotIn("Accept-encoding", req.headers)
        self.assertEqual(60, timeout)
        self.assertEqual(302, response.status_code)
        self.assertEqual("text/plain", response.headers["Content-Type"])
        self.assertEqual(["text/plain"], response.headers.getlist("Content-Type"))
        self.assertEqual("/api/services/svc_1/proxy/login?back=1", response.headers["Location"])
        self.assertNotIn("Content-Encoding", response.headers)
        self.assertEqual(b"redirect", response.data)

    @staticmethod
    def _import_container_server():
        sandbox_path = str(Path(__file__).resolve().parents[1] / "app" / "sandbox")
        if sandbox_path not in sys.path:
            sys.path.insert(0, sandbox_path)

        fake_logging = types.ModuleType("container.logging_utils")
        fake_logging.configure_logging = lambda: None
        fake_logging.log_agent = lambda *args, **kwargs: None
        fake_logging.log_event = lambda *args, **kwargs: None
        fake_logging.shorten = lambda value, limit=500: str(value or "")[:limit]
        sys.modules["container.logging_utils"] = fake_logging

        fake_claude_config = types.ModuleType("container.claude_config")
        fake_claude_config.clean_base_url = lambda value="": str(value or "").strip().rstrip("/")
        fake_claude_config.clean_config_value = lambda value="": str(value or "").strip().strip("'\"")
        fake_claude_config.claude_env = lambda: {}
        fake_claude_config.write_settings = lambda *args, **kwargs: None
        fake_claude_config.trust_projects = lambda *args, **kwargs: None
        sys.modules["container.claude_config"] = fake_claude_config

        fake_provider_health = types.ModuleType("container.provider_health")
        fake_provider_health.get_provider_health = lambda: {}
        sys.modules["container.provider_health"] = fake_provider_health

        fake_events = types.ModuleType("container.events")
        fake_events.get_events = lambda *args, **kwargs: []
        sys.modules["container.events"] = fake_events

        fake_orchestrator = types.ModuleType("container.orchestrator")

        class FakeOrchestrator:
            def get_service(self, service_id):
                return {
                    "service": {
                        "id": service_id,
                        "port": 5173,
                        "status": "running",
                    }
                }

            def get_session_info(self):
                return {"agents": [], "tools": [], "agent_count": 0}

        fake_orchestrator.Orchestrator = FakeOrchestrator
        sys.modules["container.orchestrator"] = fake_orchestrator

        sys.modules.pop("container.server", None)
        import importlib

        return importlib.import_module("container.server")


if __name__ == "__main__":
    unittest.main()
