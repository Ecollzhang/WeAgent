import unittest
from unittest.mock import patch

from flask import Flask

from app.sandbox.api import routes
from app.sandbox.host.client import OrchestratorClient
from app.sandbox.host.manager import _default_host_callback_url, _merge_no_proxy


class FakeSandboxManager:
    def __init__(self):
        self.calls = []
        self.start_error = ""

    def list_services(self, session_id, user_id=None):
        self.calls.append(("list", session_id))
        return {"session_id": session_id, "services": [{"id": "svc_1"}]}

    def get_service(self, session_id, service_id, user_id=None):
        self.calls.append(("get", session_id, service_id))
        return {"service": {"id": service_id}}

    def start_service(self, session_id, data, user_id=None):
        self.calls.append(("start", session_id, data))
        if self.start_error:
            return {"error": self.start_error}
        return {"status": "ok", "service": {"id": "svc_1", "port": data.get("port")}}

    def stop_service(self, session_id, service_id):
        self.calls.append(("stop", session_id, service_id))
        return {"status": "ok", "service": {"id": service_id, "status": "stopped"}}

    def restart_service(self, session_id, service_id, user_id=None):
        self.calls.append(("restart", session_id, service_id))
        return {"status": "ok", "service": {"id": service_id, "status": "running"}}

    def service_logs(self, session_id, service_id, tail_bytes=65536):
        self.calls.append(("logs", session_id, service_id, tail_bytes))
        return {"service_id": service_id, "stdout_tail": "out", "stderr_tail": ""}


class SandboxServiceHostStage2Test(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSandboxManager()
        routes._manager = self.fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        self.client = app.test_client()

    def tearDown(self):
        routes._manager = None

    def test_host_routes_forward_service_lifecycle_by_service_id(self):
        resp = self.client.post("/api/sandbox/sessions/s1/services/start", json={
            "agent_id": "frontend",
            "name": "preview",
            "cwd": "/workspace/agents/frontend",
            "command": "npm run dev -- --host 0.0.0.0 --port 5173",
            "port": 5173,
        })
        self.assertEqual(200, resp.status_code)
        self.assertEqual("svc_1", resp.get_json()["data"]["service"]["id"])

        resp = self.client.get("/api/sandbox/sessions/s1/services")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([("start", "s1", {
            "agent_id": "frontend",
            "name": "preview",
            "cwd": "/workspace/agents/frontend",
            "command": "npm run dev -- --host 0.0.0.0 --port 5173",
            "port": 5173,
        }), ("list", "s1")], self.fake.calls)

        resp = self.client.get("/api/sandbox/sessions/s1/services/svc_1")
        self.assertEqual(200, resp.status_code)
        resp = self.client.post("/api/sandbox/sessions/s1/services/svc_1/restart")
        self.assertEqual(200, resp.status_code)
        resp = self.client.get("/api/sandbox/sessions/s1/services/svc_1/logs?tail_bytes=123")
        self.assertEqual(200, resp.status_code)
        resp = self.client.post("/api/sandbox/sessions/s1/services/svc_1/stop")
        self.assertEqual(200, resp.status_code)

        self.assertIn(("get", "s1", "svc_1"), self.fake.calls)
        self.assertIn(("restart", "s1", "svc_1"), self.fake.calls)
        self.assertIn(("logs", "s1", "svc_1", 123), self.fake.calls)
        self.assertIn(("stop", "s1", "svc_1"), self.fake.calls)

    def test_orchestrator_client_uses_service_id_paths(self):
        client = OrchestratorClient("localhost", 1234)
        calls = []

        def fake_request(method, path, body=None, timeout=None):
            calls.append((method, path, body))
            return {"status": "ok"}

        client._request = fake_request

        client.list_services()
        client.get_service("svc_1")
        client.start_service({"port": 5173})
        client.restart_service("svc_1")
        client.service_logs("svc_1", tail_bytes=99)
        client.stop_service("svc_1")

        self.assertEqual([
            ("GET", "/api/services", None),
            ("GET", "/api/services/svc_1", None),
            ("POST", "/api/services/start", {"port": 5173}),
            ("POST", "/api/services/svc_1/restart", None),
            ("GET", "/api/services/svc_1/logs?tail_bytes=99", None),
            ("POST", "/api/services/svc_1/stop", None),
        ], calls)

    def test_start_service_returns_400_for_container_error(self):
        self.fake.start_error = "declared service port 8081 does not match command port 8080"

        resp = self.client.post("/api/sandbox/sessions/s1/services/start", json={
            "agent_id": "frontend",
            "name": "preview",
            "cwd": "/workspace/agents/frontend",
            "command": "npm run serve -- --host 0.0.0.0 --port 8080",
            "port": 8081,
        })

        self.assertEqual(400, resp.status_code)
        self.assertIn("does not match command port", resp.get_json()["message"])

    def test_default_host_callback_url_matches_backend_default_port(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                "http://host.docker.internal:5002",
                _default_host_callback_url(),
            )

        with patch.dict("os.environ", {"PORT": "5010"}, clear=True):
            self.assertEqual(
                "http://host.docker.internal:5010",
                _default_host_callback_url(),
            )

    def test_no_proxy_includes_sandbox_callback_hosts(self):
        merged = _merge_no_proxy("api.example.com,localhost")
        parts = set(merged.split(","))

        self.assertIn("api.example.com", parts)
        self.assertIn("localhost", parts)
        self.assertIn("127.0.0.1", parts)
        self.assertIn("host.docker.internal", parts)
        self.assertIn("gateway.docker.internal", parts)


if __name__ == "__main__":
    unittest.main()
