import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.sandbox.container.agent import AgentRuntime
from app.sandbox.container.providers import CodexRunner, ProviderRunnerFactory


class CodexRunnerStage4Test(unittest.TestCase):
    def test_factory_creates_codex_runner(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        self.assertIsInstance(runtime.provider_runner, CodexRunner)
        self.assertEqual("codex", ProviderRunnerFactory.create("codex", runtime).provider_name)
        self.assertEqual("provider_started", runtime.provider_runner.started_event)
        self.assertEqual("provider_output_delta", runtime.provider_runner.stdout_delta_event)
        self.assertEqual("provider_output", runtime.provider_runner.output_event)

    def test_fresh_command_uses_codex_exec_json_without_ephemeral(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch("app.sandbox.container.providers.codex.os.path.exists", return_value=False):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertFalse(used_resume)
        self.assertEqual(["codex", "exec"], command[:2])
        self.assertIn("--json", command)
        self.assertIn("--cd", command)
        self.assertIn("/workspace/agents/coder", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertNotIn("--ephemeral", command)

    def test_resume_command_uses_codex_exec_resume_last(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch("app.sandbox.container.providers.codex.os.path.exists", return_value=True):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertTrue(used_resume)
        self.assertEqual(["codex", "exec", "resume"], command[:3])
        self.assertIn("--last", command)
        self.assertIn("--json", command)
        self.assertNotIn("--cd", command)

    def test_environment_uses_private_codex_home(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        with patch.dict("os.environ", {}, clear=True):
            env = runtime.provider_runner.environment()

        self.assertEqual(
            "/workspace/agents/coder/.weagent/providers/codex/home",
            env["CODEX_HOME"],
        )
        self.assertEqual("agent-1", env["WEAGENT_AGENT_ID"])

    def test_setup_writes_codex_home_config_and_auth_from_deepseek_env(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime._agent_dir = os.path.join(tmpdir, "coder")
            with patch("app.sandbox.container.providers.codex.log_agent"), patch.dict("os.environ", {
                "DEEPSEEK_API_KEY": "sk-test",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
                "DEEPSEEK_MODEL": "deepseek-chat",
            }, clear=True), \
                 patch.object(runtime.provider_runner, "_ensure_relay", return_value="http://127.0.0.1:4446/v1"):
                runtime.provider_runner.setup()

            home_dir = runtime.provider_runner.home_dir
            with open(os.path.join(home_dir, "config.toml"), "r", encoding="utf-8") as f:
                config = f.read()
            with open(os.path.join(home_dir, "auth.json"), "r", encoding="utf-8") as f:
                auth = json.load(f)

        self.assertIn('approval_policy = "never"', config)
        self.assertIn('sandbox_mode = "danger-full-access"', config)
        self.assertIn('model = "deepseek-chat"', config)
        self.assertIn('model_provider = "deepseek"', config)
        self.assertIn('wire_api = "responses"', config)
        self.assertIn('base_url = "http://127.0.0.1:4446/v1"', config)
        self.assertEqual({"OPENAI_API_KEY": "sk-test"}, auth)
        self.assertTrue(runtime.provider_runner.runnable)

    def test_setup_fails_fast_without_codex_credentials(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime._agent_dir = os.path.join(tmpdir, "coder")
            with patch("app.sandbox.container.providers.codex.log_agent"), patch.dict("os.environ", {}, clear=True):
                runtime.provider_runner.setup()

        self.assertFalse(runtime.provider_runner.runnable)
        self.assertIn("Codex is not authenticated", runtime.provider_runner.unavailable_message())

    def test_environment_maps_deepseek_to_codex_openai_compatible_vars(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
            "DEEPSEEK_MODEL": "deepseek-chat",
        }, clear=True), \
             patch.object(runtime.provider_runner, "_ensure_relay", return_value="http://127.0.0.1:4446/v1"):
            env = runtime.provider_runner.environment()

        self.assertEqual("sk-test", env["OPENAI_API_KEY"])
        self.assertEqual("http://127.0.0.1:4446/v1", env["OPENAI_BASE_URL"])
        self.assertEqual("deepseek-chat", env["OPENAI_MODEL"])

    def test_environment_uses_anthropic_auth_token_for_codex(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {
            "ANTHROPIC_AUTH_TOKEN": "sk-anthropic-token",
            "ANTHROPIC_BASE_URL": "https://testvideo.site",
            "ANTHROPIC_MODEL": "gpt-5.5",
        }, clear=True):
            env = runtime.provider_runner.environment()

        self.assertEqual("sk-anthropic-token", env["OPENAI_API_KEY"])
        self.assertEqual("sk-anthropic-token", env["CODEX_API_KEY"])
        self.assertEqual("https://testvideo.site", env["OPENAI_BASE_URL"])
        self.assertEqual("gpt-5.5", env["OPENAI_MODEL"])

    def test_codex_base_url_normalizes_anthropic_url_from_any_env_source(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        cases = [
            ("CODEX_BASE_URL", "https://api.deepseek.com/anthropic"),
            ("OPENAI_BASE_URL", "https://api.deepseek.com/anthropic"),
            ("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
        ]

        for key, value in cases:
            with self.subTest(key=key), patch.dict("os.environ", {
                key: value,
                "DEEPSEEK_API_KEY": "sk-test",
            }, clear=True):
                self.assertEqual("https://api.deepseek.com/v1", runtime.provider_runner._codex_base_url())

    def test_environment_overrides_stale_anthropic_openai_url_for_codex_process(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://api.deepseek.com/anthropic",
            "OPENAI_MODEL": "deepseek-chat",
        }, clear=True), \
             patch.object(runtime.provider_runner, "_ensure_relay", return_value="http://127.0.0.1:4446/v1"):
            env = runtime.provider_runner.environment()

        self.assertEqual("http://127.0.0.1:4446/v1", env["OPENAI_BASE_URL"])
        self.assertEqual("http://127.0.0.1:4446/v1", env["CODEX_BASE_URL"])

    def test_non_deepseek_codex_base_url_is_used_directly_without_relay(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {
            "CODEX_API_KEY": "sk-test",
            "CODEX_BASE_URL": "https://api.openai.com/v1",
            "CODEX_MODEL": "gpt-5.1-codex",
        }, clear=True), \
             patch.object(runtime.provider_runner, "_ensure_relay") as ensure_relay:
            env = runtime.provider_runner.environment()

        self.assertEqual("https://api.openai.com/v1", env["OPENAI_BASE_URL"])
        ensure_relay.assert_not_called()

    def test_deepseek_runtime_uses_relay_but_upstream_remains_deepseek_v1(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
            "DEEPSEEK_MODEL": "deepseek-chat",
        }, clear=True), \
             patch.object(runtime.provider_runner, "_ensure_relay", return_value="http://127.0.0.1:4446/v1") as ensure_relay:
            env = runtime.provider_runner.environment()

        ensure_relay.assert_called_once_with("https://api.deepseek.com/v1")
        self.assertEqual("http://127.0.0.1:4446/v1", env["CODEX_BASE_URL"])

    def test_codex_uses_provider_specific_timeout(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        with patch.dict("os.environ", {"CODEX_EXEC_TIMEOUT_SECONDS": "17"}):
            self.assertEqual(17, runtime.provider_runner.timeout_seconds())

    def test_clean_output_extracts_text_from_jsonl(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        raw = "\n".join([
            json.dumps({"type": "delta", "delta": "hello"}),
            json.dumps({"type": "item", "item": {"text": "world"}}),
            "plain text",
        ])

        output = runtime.provider_runner.clean_output(raw)

        self.assertEqual("hello\nworld\nplain text", output)

    def test_codex_filters_pretty_json_control_events_and_reconnect_errors(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        raw = """
Reading additional input from stdin...
{
"type":"thread.started","thread_id":"019e6ccf"
}
{
"type":"error","message":"Reconnecting... 2/5 (request timed out)"
}
{
"type":"message","content":"最终结果"
}
输出中...
"""

        output = runtime.provider_runner.clean_output(raw)

        self.assertEqual("最终结果", output)

    def test_codex_stream_parser_buffers_pretty_json_until_complete(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")
        runtime.provider_runner._stream_parser = None

        first = runtime.provider_runner.stream_chunk('{\n"type":"message",\n', "stdout")
        second = runtime.provider_runner.stream_chunk('"content":"hello"\n}\n', "stdout")

        self.assertEqual("", first)
        self.assertEqual("hello\n", second)

    def test_resume_failure_markers_trigger_retry(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="codex")

        self.assertTrue(runtime.provider_runner.should_retry_without_resume("session not found"))
        self.assertTrue(runtime.provider_runner.should_retry_without_resume("failed to resume"))
        self.assertFalse(runtime.provider_runner.should_retry_without_resume("ordinary stderr"))


if __name__ == "__main__":
    unittest.main()
