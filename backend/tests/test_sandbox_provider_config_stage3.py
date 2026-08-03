import tempfile
import unittest
from unittest.mock import patch
import os

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

    def test_update_model_config_propagates_codex_provider_env(self):
        with patch("app.sandbox.container.orchestrator.os.makedirs"), \
             patch("app.sandbox.container.orchestrator.trust_projects"), \
             patch("app.sandbox.container.orchestrator.register_builtin_tools"), \
             patch("app.sandbox.container.orchestrator.log_event"), \
             patch("app.sandbox.container.orchestrator.write_settings"), \
             patch.dict(os.environ, {}, clear=True):
            orchestrator = Orchestrator()
            result = orchestrator.update_model_config({
                "api_key": "sk-claude",
                "base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
                "model": "mimo-v2.5-pro",
                "CODEX_API_KEY": "sk-codex",
                "CODEX_BASE_URL": "https://token-plan-cn.xiaomimimo.com/v1",
                "CODEX_MODEL": "mimo-v2.5-pro",
                "CODEX_USE_RELAY": "1",
            })

            self.assertEqual("ok", result["status"])
            self.assertEqual("https://token-plan-cn.xiaomimimo.com/v1", os.environ["CODEX_BASE_URL"])
            self.assertEqual("mimo-v2.5-pro", os.environ["CODEX_MODEL"])
            self.assertEqual("sk-codex", os.environ["CODEX_API_KEY"])
            self.assertEqual("1", os.environ["CODEX_USE_RELAY"])
            self.assertEqual("https://token-plan-cn.xiaomimimo.com/v1", result["codex_base_url"])

    def test_update_runtime_config_refreshes_only_user_authorization(self):
        with patch("app.sandbox.container.orchestrator.os.makedirs"), \
             patch("app.sandbox.container.orchestrator.trust_projects"), \
             patch("app.sandbox.container.orchestrator.register_builtin_tools"), \
             patch("app.sandbox.container.orchestrator.log_event"), \
             patch.dict(os.environ, {}, clear=True):
            orchestrator = Orchestrator()
            result = orchestrator.update_runtime_config({
                "USER_AUTH_TOKEN": "Bearer fresh-token",
                "RAG_SCOPE_DOMAIN": "forbidden-override",
            })

            self.assertEqual({"status": "ok", "updated": ["USER_AUTH_TOKEN"]}, result)
            self.assertEqual("Bearer fresh-token", os.environ["USER_AUTH_TOKEN"])
            self.assertNotIn("RAG_SCOPE_DOMAIN", os.environ)

    def test_unexpected_provider_status_is_runtime_error(self):
        self.assertTrue(Orchestrator._is_agent_runtime_error(
            "unexpected status 404 Not Found, url: https://example.com/responses"
        ))


if __name__ == "__main__":
    unittest.main()
