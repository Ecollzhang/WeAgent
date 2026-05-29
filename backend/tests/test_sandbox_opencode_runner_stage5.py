import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.sandbox.container.agent import AgentRuntime
from app.sandbox.container.providers import OpenCodeRunner, ProviderRunnerFactory


class OpenCodeRunnerStage5Test(unittest.TestCase):
    def test_factory_creates_opencode_runner(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        self.assertIsInstance(runtime.provider_runner, OpenCodeRunner)
        self.assertEqual("opencode", ProviderRunnerFactory.create("opencode", runtime).provider_name)
        self.assertEqual("provider_started", runtime.provider_runner.started_event)
        self.assertEqual("provider_output_delta", runtime.provider_runner.stdout_delta_event)
        self.assertEqual("provider_output", runtime.provider_runner.output_event)

    def test_fresh_command_uses_opencode_run_json(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch("app.sandbox.container.providers.opencode.os.path.exists", return_value=False), \
             patch.dict("os.environ", {}, clear=True):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertFalse(used_resume)
        self.assertEqual(["opencode", "run"], command[:2])
        self.assertIn("--format", command)
        self.assertIn("json", command)
        self.assertIn("--dir", command)
        self.assertIn("/workspace/agents/coder", command)
        self.assertIn("--dangerously-skip-permissions", command)
        self.assertNotIn("-c", command)
        self.assertIn("OpenCode final response rule", command[-1])

    def test_command_uses_configured_opencode_model_arg(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch("app.sandbox.container.providers.opencode.os.path.exists", return_value=False), \
             patch.dict("os.environ", {
                 "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
                 "DEEPSEEK_MODEL": "deepseek-chat",
             }, clear=True):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertFalse(used_resume)
        self.assertIn("--model", command)
        self.assertIn("deepseek/deepseek-chat", command)

    def test_resume_command_uses_continue_flag(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch("app.sandbox.container.providers.opencode.os.path.exists", return_value=True):
            command, used_resume = runtime.provider_runner.build_command("hello")

        self.assertTrue(used_resume)
        self.assertEqual(["opencode", "run"], command[:2])
        self.assertIn("-c", command)

    def test_command_requires_normal_final_assistant_text(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch("app.sandbox.container.providers.opencode.os.path.exists", return_value=False), \
             patch.dict("os.environ", {}, clear=True):
            command, _ = runtime.provider_runner.build_command("hello")

        self.assertIn("normal assistant text reply", command[-1])
        self.assertNotIn("WEAGENT_FINAL_REPLY:", command[-1])

    def test_environment_uses_private_opencode_home(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        with patch.dict("os.environ", {}, clear=True):
            env = runtime.provider_runner.environment()

        self.assertEqual(
            "/workspace/agents/coder/.weagent/providers/opencode/home",
            env["OPENCODE_HOME"],
        )
        self.assertEqual("agent-1", env["WEAGENT_AGENT_ID"])

    def test_environment_maps_shared_provider_vars_to_opencode(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch.dict("os.environ", {
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
            "DEEPSEEK_MODEL": "deepseek-chat",
        }, clear=True):
            env = runtime.provider_runner.environment()

        self.assertEqual("sk-test", env["OPENCODE_API_KEY"])
        self.assertEqual("sk-test", env["OPENAI_API_KEY"])
        self.assertEqual("https://api.deepseek.com/v1", env["OPENCODE_BASE_URL"])
        self.assertEqual("deepseek-chat", env["OPENCODE_MODEL"])
        self.assertEqual("/workspace/agents/coder/.weagent/providers/opencode/home", env["HOME"])

    def test_environment_uses_anthropic_auth_token_for_opencode(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch.dict("os.environ", {
            "ANTHROPIC_AUTH_TOKEN": "sk-anthropic-token",
            "ANTHROPIC_BASE_URL": "https://testvideo.site",
            "ANTHROPIC_MODEL": "gpt-5.5",
        }, clear=True):
            env = runtime.provider_runner.environment()

        self.assertEqual("sk-anthropic-token", env["OPENCODE_API_KEY"])
        self.assertEqual("sk-anthropic-token", env["OPENAI_API_KEY"])
        self.assertEqual("https://testvideo.site", env["OPENCODE_BASE_URL"])
        self.assertEqual("gpt-5.5", env["OPENCODE_MODEL"])

    def test_opencode_base_url_normalizes_deepseek_anthropic_url_from_any_env_source(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        cases = [
            ("OPENCODE_BASE_URL", "https://api.deepseek.com/anthropic"),
            ("OPENAI_BASE_URL", "https://api.deepseek.com/anthropic"),
            ("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic"),
            ("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
        ]

        for key, value in cases:
            with self.subTest(key=key), patch.dict("os.environ", {key: value}, clear=True):
                self.assertEqual("https://api.deepseek.com/v1", runtime.provider_runner._opencode_base_url())

    def test_setup_writes_opencode_config_for_openai_compatible_provider(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime._agent_dir = os.path.join(tmpdir, "coder")
            with patch("app.sandbox.container.providers.opencode.log_agent"), patch.dict("os.environ", {
                "DEEPSEEK_API_KEY": "sk-test",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com/anthropic",
                "DEEPSEEK_MODEL": "deepseek-chat",
            }, clear=True):
                runtime.provider_runner.setup()

            config_path = os.path.join(
                runtime.provider_runner.home_dir,
                ".config",
                "opencode",
                "opencode.json",
            )
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        self.assertEqual("deepseek/deepseek-chat", config["model"])
        self.assertEqual("https://api.deepseek.com/v1", config["provider"]["deepseek"]["options"]["baseURL"])
        self.assertEqual("{env:OPENCODE_API_KEY}", config["provider"]["deepseek"]["options"]["apiKey"])

    def test_setup_writes_opencode_config_from_anthropic_auth_token(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime._agent_dir = os.path.join(tmpdir, "coder")
            with patch("app.sandbox.container.providers.opencode.log_agent"), patch.dict("os.environ", {
                "ANTHROPIC_AUTH_TOKEN": "sk-anthropic-token",
                "ANTHROPIC_BASE_URL": "https://testvideo.site",
                "ANTHROPIC_MODEL": "gpt-5.5",
            }, clear=True):
                runtime.provider_runner.setup()

            config_path = os.path.join(
                runtime.provider_runner.home_dir,
                ".config",
                "opencode",
                "opencode.json",
            )
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        self.assertEqual("openai_compatible/gpt-5.5", config["model"])
        self.assertEqual(
            "https://testvideo.site",
            config["provider"]["openai_compatible"]["options"]["baseURL"],
        )
        self.assertEqual("{env:OPENCODE_API_KEY}", config["provider"]["openai_compatible"]["options"]["apiKey"])

    def test_opencode_uses_provider_specific_timeout(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        with patch.dict("os.environ", {"OPENCODE_EXEC_TIMEOUT_SECONDS": "19"}):
            self.assertEqual(19, runtime.provider_runner.timeout_seconds())

    def test_clean_output_extracts_text_from_jsonl(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        raw = "\n".join([
            json.dumps({"type": "message", "message": "hello"}),
            json.dumps({"type": "part", "part": {"text": "world"}}),
            "plain text",
        ])

        output = runtime.provider_runner.clean_output(raw)

        self.assertEqual("hello\nworld\nplain text", output)

    def test_opencode_filters_tool_json_and_keeps_text_parts(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        raw = "\n".join([
            json.dumps({"type": "tool_use", "tool": "write", "input": {"path": "x"}}),
            json.dumps({"type": "part", "part": {"type": "tool_use", "content": "hidden"}}),
            json.dumps({"type": "part", "part": {"type": "text", "text": "visible text"}}),
            json.dumps({"type": "message", "message": {"content": [{"type": "text", "text": "final"}]}}),
        ])

        output = runtime.provider_runner.clean_output(raw)

        self.assertEqual("visible text\nfinal", output)

    def test_opencode_stream_parser_does_not_emit_tool_events(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        runtime.provider_runner._stream_parser = None

        hidden = runtime.provider_runner.stream_chunk(
            json.dumps({"type": "tool_use", "content": "hidden"}) + "\n",
            "stdout",
        )
        visible = runtime.provider_runner.stream_chunk(
            json.dumps({"type": "message", "content": "shown"}) + "\n",
            "stdout",
        )

        self.assertEqual("", hidden)
        self.assertEqual("shown\n", visible)

    def test_opencode_filters_database_migration_stderr_noise(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        stderr = "\n".join([
            "Performing one time database migration, may take a few minutes...",
            "sqlite-migration:done",
            "Database migration complete.",
        ])

        self.assertEqual("", runtime.provider_runner.stream_chunk(stderr, "stderr"))
        self.assertEqual("", runtime.provider_runner.clean_error_output(stderr))
        self.assertEqual(
            "real error",
            runtime.provider_runner.clean_error_output(stderr + "\nreal error"),
        )

    def test_opencode_stream_filters_split_database_migration_stderr_noise(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        runtime.provider_runner._stderr_line_buffer = ""

        first = runtime.provider_runner.stream_chunk("P", "stderr")
        second = runtime.provider_runner.stream_chunk(
            "erforming one time database migration, may take a few minutes...\n",
            "stderr",
        )
        third = runtime.provider_runner.stream_chunk("real error\n", "stderr")

        self.assertEqual("", first)
        self.assertEqual("", second)
        self.assertEqual("real error", third)

    def test_opencode_extracts_api_error_json(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        raw = json.dumps({
            "type": "error",
            "error": {
                "name": "APIError",
                "data": {
                    "message": "Not Found",
                    "statusCode": 404,
                    "metadata": {
                        "url": "https://api.deepseek.com/anthropic/chat/completions",
                    },
                },
            },
        })

        output = runtime.provider_runner.clean_output(raw)

        self.assertEqual(
            "[Error] APIError: Not Found (404): https://api.deepseek.com/anthropic/chat/completions",
            output,
        )

    def test_opencode_fallback_output_does_not_use_weagent_report_result(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        raw = json.dumps({
            "type": "tool_use",
            "part": {
                "state": {
                    "output": json.dumps({
                        "element": {
                            "type": "result",
                            "title": "能力说明",
                            "content": "向用户介绍 CSS样式大师 Agent 的能力范围",
                        },
                        "status": "ok",
                    }) + "\n",
                },
            },
        })

        self.assertEqual("", runtime.provider_runner.clean_output(raw))
        self.assertEqual("", runtime.provider_runner.fallback_output(raw))

    def test_opencode_fallback_output_ignores_placeholder_report_result(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")
        raw = json.dumps({
            "type": "tool_use",
            "part": {
                "state": {
                    "output": json.dumps({
                        "element": {
                            "type": "result",
                            "title": "接收用户询问完成",
                            "content": "已准备回复用户",
                        },
                        "status": "ok",
                    }) + "\n",
                },
            },
        })

        self.assertEqual("", runtime.provider_runner.clean_output(raw))
        self.assertEqual("", runtime.provider_runner.fallback_output(raw))

    def test_resume_failure_markers_trigger_retry(self):
        runtime = AgentRuntime("agent-1", "Coder", "system", "coder", provider_name="opencode")

        self.assertTrue(runtime.provider_runner.should_retry_without_resume("session not found"))
        self.assertTrue(runtime.provider_runner.should_retry_without_resume("cannot continue"))
        self.assertFalse(runtime.provider_runner.should_retry_without_resume("ordinary stderr"))


if __name__ == "__main__":
    unittest.main()
