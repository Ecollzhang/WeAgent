import unittest
from unittest.mock import patch

from app.sandbox.container.agent import ClaudeRuntime
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


if __name__ == "__main__":
    unittest.main()
