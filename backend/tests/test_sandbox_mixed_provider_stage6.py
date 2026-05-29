import unittest
from unittest.mock import patch

from app.sandbox.container.orchestrator import Orchestrator


def _isolated_orchestrator():
    patches = [
        patch("app.sandbox.container.orchestrator.os.makedirs"),
        patch("app.sandbox.container.orchestrator.trust_projects"),
        patch("app.sandbox.container.orchestrator.register_builtin_tools"),
        patch("app.sandbox.container.orchestrator.log_event"),
        patch("app.sandbox.container.orchestrator.log_agent"),
        patch("app.sandbox.container.orchestrator.session_store.save_agent_config"),
        patch("app.sandbox.container.orchestrator.session_store.save_message"),
        patch("app.sandbox.container.orchestrator.session_store.get_recent_context", return_value=""),
        patch("app.sandbox.container.agent.log_agent"),
        patch("app.sandbox.container.providers.claude_code.write_settings"),
        patch("app.sandbox.container.providers.claude_code.trust_projects"),
        patch("app.sandbox.container.providers.claude_code.open", create=True),
        patch("app.sandbox.container.providers.claude_code.os.path.exists", return_value=False),
        patch("app.sandbox.container.providers.codex.CodexRunner._write_file"),
        patch("app.sandbox.container.providers.codex.log_agent"),
        patch("app.sandbox.container.providers.opencode.OpenCodeRunner._write_noninteractive_config"),
        patch.dict("os.environ", {"CODEX_API_KEY": "sk-test"}),
    ]
    for item in patches:
        item.start()
    return Orchestrator(), patches


class MixedProviderStage6Test(unittest.TestCase):
    def tearDown(self):
        for item in getattr(self, "_patches", []):
            item.stop()

    def _make_orchestrator(self):
        orchestrator, self._patches = _isolated_orchestrator()
        return orchestrator

    def test_mixed_session_keeps_provider_and_workspace_isolated(self):
        orchestrator = self._make_orchestrator()
        configs = [
            ("moderator", "主持", "moderator", "claude"),
            ("frontend", "前端开发专家", "frontend", "claude"),
            ("writer", "文档助手", "writer", "codex"),
            ("reviewer", "评审助手", "reviewer", "opencode"),
        ]

        for agent_id, role, workspace, provider in configs:
            result = orchestrator.create_agent(agent_id, role, "system", workspace, adapter_name=provider)
            self.assertEqual("ok", result["status"])
            self.assertEqual(provider, result["agent"]["provider"])
            self.assertEqual(f"/workspace/agents/{workspace}", result["agent"]["work_dir"])

        agents = {agent["agent_id"]: agent for agent in orchestrator.get_session_info()["agents"]}
        self.assertEqual("claude", agents["moderator"]["provider"])
        self.assertEqual("claude", agents["frontend"]["provider"])
        self.assertEqual("codex", agents["writer"]["provider"])
        self.assertEqual("opencode", agents["reviewer"]["provider"])

        writer = orchestrator.agents["writer"].provider_runner
        reviewer = orchestrator.agents["reviewer"].provider_runner
        self.assertEqual("/workspace/agents/writer/.weagent/providers/codex/home", writer.home_dir)
        self.assertEqual("/workspace/agents/reviewer/.weagent/providers/opencode/home", reviewer.home_dir)
        self.assertNotEqual(writer.home_dir, reviewer.home_dir)
        self.assertTrue(writer.resume_marker.endswith("/.weagent/providers/codex/session_marker"))
        self.assertTrue(reviewer.resume_marker.endswith("/.weagent/providers/opencode/session_marker"))

    def test_mixed_session_sends_each_agent_with_its_configured_provider(self):
        orchestrator = self._make_orchestrator()
        orchestrator.create_agent("frontend", "Same Role", "system", "frontend", adapter_name="claude")
        orchestrator.create_agent("writer", "Same Role", "system", "writer", adapter_name="codex")
        orchestrator.create_agent("reviewer", "Same Role", "system", "reviewer", adapter_name="opencode")

        seen = []

        def fake_call(runtime, message, retry_without_continue=True):
            seen.append((runtime.agent_id, runtime.provider_runner.provider_name, runtime.workspace_name))
            return f"{runtime.agent_id}:{runtime.provider_runner.provider_name}"

        with patch("app.sandbox.container.agent.AgentRuntime._call_claude", new=fake_call), \
             patch.object(orchestrator, "_detect_written_files", return_value=[]), \
             patch.object(orchestrator, "_execute_tool_calls", return_value=[]), \
             patch.object(orchestrator, "_parse_and_write_code_blocks", return_value=[]), \
             patch.object(orchestrator, "_second_pass_extract_files", return_value=[]), \
             patch("app.sandbox.container.orchestrator.push_event"):
            results = [
                orchestrator.send_to_agent("frontend", "task"),
                orchestrator.send_to_agent("writer", "task"),
                orchestrator.send_to_agent("reviewer", "task"),
            ]

        self.assertEqual(["ok", "ok", "ok"], [item["status"] for item in results])
        self.assertEqual([
            ("frontend", "claude", "frontend"),
            ("writer", "codex", "writer"),
            ("reviewer", "opencode", "reviewer"),
        ], seen)

    def test_delegation_targets_keep_provider_boundaries(self):
        orchestrator = self._make_orchestrator()
        orchestrator.create_agent("moderator", "主持", "system", "moderator", adapter_name="claude")
        orchestrator.create_agent("frontend", "前端开发专家", "system", "frontend", adapter_name="claude")
        orchestrator.create_agent("writer", "文档助手", "system", "writer", adapter_name="codex")

        seen = []

        def fake_call(runtime, message, retry_without_continue=True):
            seen.append((runtime.agent_id, runtime.provider_runner.provider_name, message))
            if runtime.agent_id == "moderator":
                return "前端负责页面，文档负责开发文档。"
            return f"{runtime.agent_id}:{runtime.provider_runner.provider_name}:done"

        with patch("app.sandbox.container.agent.AgentRuntime._call_claude", new=fake_call), \
             patch.object(orchestrator, "_detect_written_files", return_value=[]), \
             patch.object(orchestrator, "_execute_tool_calls", return_value=[]), \
             patch.object(orchestrator, "_parse_and_write_code_blocks", return_value=[]), \
             patch.object(orchestrator, "_second_pass_extract_files", return_value=[]), \
             patch("app.sandbox.container.orchestrator.push_event"):
            result = orchestrator.delegate_task("写一个商城登录页面，并写开发文档", moderator_id="moderator")

        self.assertEqual("ok", result["status"])
        self.assertEqual(["frontend", "writer"], [item["agent_id"] for item in result["results"]])
        self.assertEqual([
            ("moderator", "claude"),
            ("frontend", "claude"),
            ("writer", "codex"),
        ], [(agent_id, provider) for agent_id, provider, _ in seen])
        writer_prompt = [message for agent_id, _, message in seen if agent_id == "writer"][0]
        frontend_prompt = [message for agent_id, _, message in seen if agent_id == "frontend"][0]
        self.assertIn("/workspace/agents/writer/", writer_prompt)
        self.assertIn("/workspace/agents/frontend/", frontend_prompt)


if __name__ == "__main__":
    unittest.main()
