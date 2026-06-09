import os
import tempfile
import unittest
from unittest.mock import patch

from app.sandbox.container.agent import ClaudeRuntime
from app.sandbox.container.capabilities import write_projection
from app.sandbox.container.providers import ClaudeCodeRunner, ProviderRunnerFactory


class ProviderRunnerStage2Test(unittest.TestCase):
    def test_factory_creates_claude_runner(self):
        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")
        runner = ProviderRunnerFactory.create("claude", runtime)

        self.assertIsInstance(runner, ClaudeCodeRunner)
        self.assertEqual("claude", runner.provider_name)

    def test_claude_runner_fresh_command_omits_continue_flag(self):
        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")

        with patch("app.sandbox.container.providers.claude_code.os.path.exists", return_value=False):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertFalse(used_resume)
        self.assertEqual("claude", command[0])
        self.assertNotIn("-c", command)
        self.assertIn("-p", command)

    def test_claude_runner_resume_command_uses_continue_flag(self):
        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")

        with patch("app.sandbox.container.providers.claude_code.os.path.exists", return_value=True):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertTrue(used_resume)
        self.assertEqual("claude", command[0])
        self.assertIn("-c", command)
        self.assertIn("-p", command)

    def test_claude_runner_resume_failure_markers(self):
        runner_cls = ClaudeCodeRunner

        self.assertTrue(runner_cls._should_retry_without_continue("conversation not found"))
        self.assertTrue(runner_cls._should_retry_without_continue("could not continue"))
        self.assertTrue(runner_cls._should_retry_without_continue("no previous conversation"))
        self.assertFalse(runner_cls._should_retry_without_continue("ordinary stderr"))

    def test_claude_runtime_keeps_compatibility_retry_helper(self):
        self.assertTrue(ClaudeRuntime._should_retry_without_continue("conversation not found"))
        self.assertFalse(ClaudeRuntime._should_retry_without_continue("ordinary stderr"))

    def test_runners_emit_neutral_provider_events(self):
        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")
        runner = runtime.provider_runner

        self.assertEqual("provider_started", runner.started_event)
        self.assertEqual("provider_output_delta", runner.stdout_delta_event)
        self.assertEqual("provider_error_delta", runner.stderr_delta_event)
        self.assertEqual("provider_output", runner.output_event)
        self.assertEqual("provider_error", runner.error_event)
        self.assertEqual("provider_stopped", runner.stopped_event)

    def test_claude_setup_writes_capability_bootstrap_to_prompt_files(self):
        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")
        projection = {
            "schema_version": "weagent.capability_projection/v1",
            "session_id": "session-1",
            "capabilities": {},
            "skills": {
                "skill-1": {
                    "runtime_id": "skill-1",
                    "capability_id": "skill-1",
                    "version_id": "version-1",
                    "name": "Desktop Smoke Skill",
                    "content": "# Desktop Smoke Skill\nReturn DESKTOP_SKILL_OK.",
                    "assets": [],
                }
            },
            "mcp": {},
            "plugins": {},
            "tools": {},
            "agents": {
                "agent-1": {
                    "agent_id": "agent-1",
                    "capabilities": [
                        {
                            "runtime_id": "skill-1",
                            "capability_id": "skill-1",
                            "capability_version_id": "version-1",
                            "type": "skill",
                            "name": "Desktop Smoke Skill",
                            "granted_permissions": [],
                        }
                    ],
                    "skill_index": [
                        {
                            "runtime_id": "skill-1",
                            "capability_id": "skill-1",
                            "version_id": "version-1",
                            "name": "Desktop Smoke Skill",
                            "path": "/workspace/.weagent/skills/skill-1/SKILL.md",
                        }
                    ],
                    "tool_index": [],
                    "permissions": {"agent_id": "agent-1", "grants": []},
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime._agent_dir = os.path.join(tmpdir, "frontend")
            write_projection(projection, workspace_root=tmpdir)
            with patch("app.sandbox.container.providers.claude_code.write_settings"), \
                 patch("app.sandbox.container.providers.claude_code.trust_projects"):
                runtime.provider_runner.setup()

            with open(os.path.join(runtime._agent_dir, ".claude", "agent.md"), encoding="utf-8") as handle:
                agent_md = handle.read()
            with open(os.path.join(runtime._agent_dir, "CLAUDE.md"), encoding="utf-8") as handle:
                claude_md = handle.read()

        for content in (agent_md, claude_md):
            self.assertIn("WeAgent capability runtime is available for this agent.", content)
            self.assertIn("/workspace/.weagent/agents/agent-1/capabilities.json", content)
            self.assertIn("/workspace/.weagent/agents/agent-1/skill-index.json", content)
            self.assertIn("/workspace/.weagent/agents/agent-1/tool-index.json", content)
            self.assertIn("/workspace/.weagent/agents/agent-1/permissions.json", content)


if __name__ == "__main__":
    unittest.main()
