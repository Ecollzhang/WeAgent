import importlib.machinery
import importlib.util
import inspect
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.sandbox.container.orchestrator import Orchestrator
from app.services.sandbox_event_bridge import SandboxEventBridge


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def load_script_module(name, relative_path):
    path = BACKEND_ROOT / relative_path
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class SandboxServiceAgentStage6Test(unittest.TestCase):
    def test_weagent_report_accepts_service_payload(self):
        report = load_script_module("weagent_report_stage6", "app/sandbox/bin/weagent-report")

        errors = report.validate_payload({
            "type": "service",
            "title": "Frontend Preview",
            "content": "Service is running",
            "status": "running",
            "data": {"service_id": "svc_1", "port": 5173},
        })

        self.assertEqual([], errors)

    def test_weagent_report_rejects_service_without_id(self):
        report = load_script_module("weagent_report_stage6_invalid", "app/sandbox/bin/weagent-report")

        errors = report.validate_payload({
            "type": "service",
            "title": "Frontend Preview",
            "content": "Service is running",
            "data": {"port": 5173},
        })

        self.assertTrue(any("service requires data.service_id" in item for item in errors))

    def test_orchestrator_normalizes_service_report(self):
        orchestrator = object.__new__(Orchestrator)

        element, error = orchestrator._normalize_report_element({
            "type": "service",
            "title": "Frontend Preview",
            "content": "Service is running",
            "status": "running",
            "data": {"id": "svc_1", "port": "5173", "name": "vite"},
        })

        self.assertIsNone(error)
        self.assertEqual("service", element["type"])
        self.assertEqual("svc_1", element["data"]["service_id"])
        self.assertEqual("svc_1", element["data"]["id"])
        self.assertEqual(5173, element["data"]["port"])

    def test_orchestrator_start_service_uses_payload_signature(self):
        signature = inspect.signature(Orchestrator.start_service)
        self.assertEqual(["self", "payload"], list(signature.parameters))

    def test_event_bridge_enriches_service_element_with_proxy_url(self):
        bridge = SandboxEventBridge()
        conversation = SimpleNamespace(owner_id="u1")

        class FakeManager:
            def get_service(self, session_id, service_id, user_id=None):
                self.call = (session_id, service_id, user_id)
                return {
                    "service": {
                        "id": service_id,
                        "service_id": service_id,
                        "name": "Frontend Preview",
                        "port": 5173,
                        "status": "running",
                        "proxy_url": f"/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/?token=t",
                    }
                }

        fake_manager = FakeManager()
        element = {
            "type": "service",
            "content": "Service is running",
            "data": {"service_id": "svc_1", "port": 5173},
        }

        with patch("app.sandbox.get_manager", return_value=fake_manager):
            enriched = bridge._enrich_service_element("s1", conversation, element)

        self.assertEqual(("s1", "svc_1", "u1"), fake_manager.call)
        self.assertEqual("/api/sandbox/sessions/s1/services/svc_1/proxy/?token=t", enriched["data"]["proxy_url"])
        self.assertEqual(enriched["data"]["proxy_url"], enriched["data"]["url"])

    def test_weagent_service_start_reports_service_card(self):
        service_tool = load_script_module("weagent_service_stage6", "app/sandbox/bin/weagent-service")
        calls = []

        def fake_request(method, path, payload=None):
            calls.append((method, path, payload))
            if method == "POST" and path == "/api/services/start":
                return {
                    "status": "ok",
                    "service": {
                        "id": "svc_1",
                        "name": payload["name"],
                        "port": payload["port"],
                        "status": "starting",
                    },
                }
            if method == "GET" and path == "/api/services/svc_1":
                return {
                    "service": {
                        "id": "svc_1",
                        "name": "Frontend Preview",
                        "port": 5173,
                        "status": "running",
                    },
                }
            if method == "POST" and path == "/api/report":
                return {"status": "ok"}
            return {"error": f"unexpected {method} {path}"}

        with patch.object(service_tool, "request_json", side_effect=fake_request), \
             patch.dict("os.environ", {"WEAGENT_AGENT_ID": "agent_1", "SESSION_ID": "s1"}, clear=False), \
             patch("sys.stdout", new_callable=io.StringIO):
            code = service_tool.main([
                "start",
                "--name", "Frontend Preview",
                "--cwd", "/workspace/agents/frontend",
                "--command", "npm run dev -- --host 0.0.0.0 --port 5173",
                "--port", "5173",
                "--type", "vite",
                "--wait", "1",
            ])

        self.assertEqual(0, code)
        report_call = [call for call in calls if call[0] == "POST" and call[1] == "/api/report"][0]
        report = report_call[2]["report"]
        self.assertEqual("service", report["type"])
        self.assertEqual("svc_1", report["data"]["service_id"])
        self.assertIn("/api/sandbox/sessions/s1/services/svc_1/proxy/", report["data"]["proxy_url"])


if __name__ == "__main__":
    unittest.main()
