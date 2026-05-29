import tempfile
import unittest
from unittest.mock import patch

from app.sandbox.container.agent import AgentRuntime
from app.sandbox.container.orchestrator import Orchestrator
from app.sandbox.container.providers import CodexRunner, OpenCodeRunner


class ProviderConfigStage3Test(unittest.TestCase):
    def test_session_config_persists_adapter_name_and_defaults_to_claude(self):
        from app.sandbox.container import session as session_store

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(session_store, "SESSION_DIR", tmp), \
                 patch.object(session_store, "AGENTS_DIR", f"{tmp}/agents"), \
                 patch.object(session_store, "CONFIG_FILE", f"{tmp}/config.json"):
                session_store.save_agent_config("a1", "Writer", "prompt", "writer", "codex")
                session_store.save_agent_config("a2", "Writer", "prompt", "writer2")

                self.assertEqual("codex", session_store.load_agent_config("a1")["adapter_name"])
                self.assertEqual("claude", session_store.load_agent_config("a2")["adapter_name"])
                self.assertEqual("codex", session_store.load_agent_config("a1")["provider"])

    def test_agent_runtime_uses_configured_provider_without_role_name_mapping(self):
        runtime = AgentRuntime("writer", "Same Role", "system", "same-role", provider_name="codex")

        self.assertEqual("codex", runtime.provider_runner.provider_name)
        self.assertIsInstance(runtime.provider_runner, CodexRunner)
        self.assertEqual("codex", runtime.to_dict()["adapter_name"])

    def test_opencode_provider_is_configured_without_role_name_mapping(self):
        runtime = AgentRuntime("writer", "Writer", "system", "writer", provider_name="opencode")

        self.assertEqual("opencode", runtime.provider_runner.provider_name)
        self.assertIsInstance(runtime.provider_runner, OpenCodeRunner)
        self.assertEqual("opencode", runtime.to_dict()["adapter_name"])

    def test_orchestrator_session_info_includes_provider(self):
        with patch("app.sandbox.container.orchestrator.os.makedirs"), \
             patch("app.sandbox.container.orchestrator.trust_projects"), \
             patch("app.sandbox.container.orchestrator.register_builtin_tools"), \
             patch("app.sandbox.container.orchestrator.log_event"), \
             patch("app.sandbox.container.orchestrator.log_agent"), \
             patch("app.sandbox.container.orchestrator.session_store.save_agent_config"), \
             patch("app.sandbox.container.agent.os.makedirs"), \
             patch("app.sandbox.container.agent.log_agent"), \
             patch("app.sandbox.container.providers.claude_code.write_settings"), \
             patch("app.sandbox.container.providers.claude_code.trust_projects"), \
             patch("app.sandbox.container.providers.claude_code.open", create=True), \
             patch("app.sandbox.container.providers.claude_code.os.path.exists", return_value=False):
            orchestrator = Orchestrator()
            result = orchestrator.create_agent(
                "frontend",
                "Frontend",
                "system",
                "frontend",
                adapter_name="claude",
            )

        self.assertEqual("ok", result["status"])
        agent = result["agent"]
        self.assertEqual("claude", agent["provider"])
        self.assertEqual("claude", agent["adapter_name"])


if __name__ == "__main__":
    unittest.main()
