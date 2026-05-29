import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import app.sandbox.container.provider_health as provider_health
from app.sandbox.container.provider_health import check_provider


class ProviderHealthTest(unittest.TestCase):
    def test_check_provider_reports_available_cli_version(self):
        completed = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex 0.1.0\n",
            stderr="",
        )

        with patch("app.sandbox.container.provider_health.shutil.which", return_value="/usr/bin/codex"), \
             patch("app.sandbox.container.provider_health.subprocess.run", return_value=completed) as run:
            result = check_provider("codex")

        self.assertTrue(result["available"])
        self.assertEqual("codex 0.1.0", result["version"])
        self.assertEqual("/usr/bin/codex", result["path"])
        run.assert_called_once()
        self.assertEqual(["codex", "--version"], run.call_args.args[0])

    def test_check_provider_reports_missing_cli(self):
        with patch("app.sandbox.container.provider_health.shutil.which", return_value=None), \
             patch("app.sandbox.container.provider_health.subprocess.run") as run:
            result = check_provider("opencode")

        self.assertFalse(result["available"])
        self.assertEqual("opencode CLI not found", result["error"])
        run.assert_not_called()

    def test_check_provider_reports_version_check_failure(self):
        completed = subprocess.CompletedProcess(
            args=["claude", "--version"],
            returncode=2,
            stdout="",
            stderr="bad flags\n",
        )

        with patch("app.sandbox.container.provider_health.shutil.which", return_value="/usr/bin/claude"), \
             patch("app.sandbox.container.provider_health.subprocess.run", return_value=completed):
            result = check_provider("claude")

        self.assertFalse(result["available"])
        self.assertEqual("bad flags", result["version"])
        self.assertEqual(2, result["returncode"])

    def test_check_provider_reports_timeout(self):
        with patch("app.sandbox.container.provider_health.shutil.which", return_value="/usr/bin/claude"), \
             patch("app.sandbox.container.provider_health.subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 5)):
            result = check_provider("claude")

        self.assertFalse(result["available"])
        self.assertIn("timed out", result["error"])

    def test_get_provider_health_returns_all_supported_providers(self):
        with patch.object(provider_health, "check_provider") as check:
            check.side_effect = lambda name, spec, timeout_seconds=5: {"name": name, "available": True}
            result = provider_health.get_provider_health()

        self.assertEqual({"claude", "codex", "opencode"}, set(result))
        self.assertTrue(all(item["available"] for item in result.values()))


class ProviderHealthApiTest(unittest.TestCase):
    def setUp(self):
        import importlib

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

        fake_orchestrator = types.ModuleType("container.orchestrator")

        class FakeOrchestrator:
            def __init__(self):
                self.agents = {}

            def get_session_info(self):
                return {"agents": [], "tools": [], "agent_count": 0}

        fake_orchestrator.Orchestrator = FakeOrchestrator
        sys.modules["container.orchestrator"] = fake_orchestrator

        sys.modules.pop("container.server", None)
        server = importlib.import_module("container.server")

        self.server = server
        self.client = self.server.app.test_client()

    def test_providers_endpoint_returns_cached_provider_health(self):
        self.server.PROVIDER_HEALTH = {
            "claude": {"available": True, "version": "claude"},
            "codex": {"available": True, "version": "codex"},
            "opencode": {"available": True, "version": "opencode"},
        }

        response = self.client.get("/api/providers")

        self.assertEqual(200, response.status_code)
        data = response.get_json()
        self.assertEqual("ok", data["status"])
        self.assertEqual({"claude", "codex", "opencode"}, set(data["providers"]))

    def test_session_endpoint_includes_cached_provider_health(self):
        self.server.PROVIDER_HEALTH = {
            "claude": {"available": True, "version": "claude"},
            "codex": {"available": False, "version": ""},
            "opencode": {"available": True, "version": "opencode"},
        }

        response = self.client.get("/api/session")

        self.assertEqual(200, response.status_code)
        data = response.get_json()
        self.assertIn("providers", data)
        self.assertEqual({"claude", "codex", "opencode"}, set(data["providers"]))


if __name__ == "__main__":
    unittest.main()
