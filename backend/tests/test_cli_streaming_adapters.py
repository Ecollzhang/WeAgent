import unittest
from pathlib import Path
from unittest.mock import patch

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.adapters.claude_adapter import ClaudeAdapter
from app.adapters.codex_adapter import CodexAdapter
from app.adapters.types import AgentRequest


class _FakeStdout:
    def __init__(self, lines):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)


class _FakeStderr:
    def __init__(self, text=""):
        self._text = text

    def read(self):
        return self._text


class _FakeProcess:
    def __init__(self, lines, returncode=0, stderr=""):
        self.stdout = _FakeStdout(lines)
        self.stderr = _FakeStderr(stderr)
        self.returncode = returncode

    def wait(self):
        return self.returncode


class CliStreamingAdaptersTest(unittest.TestCase):
    def test_codex_streams_jsonl_events_with_expected_command(self):
        request = AgentRequest(
            prompt="build it",
            agent_id="codex",
            agent_name="Codex",
            workspace_path=Path("E:/workspace"),
        )
        process = _FakeProcess(
            [
                '{"type":"message_delta","delta":"hi"}\n',
                '{"type":"message_completed","content":"hi there"}\n',
            ]
        )

        with patch("app.adapters.codex_adapter.subprocess.Popen", return_value=process) as popen:
            events = list(CodexAdapter().stream(request))

        command = popen.call_args.args[0]
        kwargs = popen.call_args.kwargs
        self.assertTrue(command[0].lower().endswith(("codex", "codex.cmd", "codex.exe")))
        self.assertEqual(["exec", "--json", "--cd"], command[1:4])
        self.assertIn("--sandbox", command)
        self.assertIn("workspace-write", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual("build it", command[-1])
        self.assertEqual("utf-8", kwargs["encoding"])
        self.assertEqual("replace", kwargs["errors"])
        self.assertEqual(["agent.started", "message.delta", "message.completed"], [event["type"] for event in events])

    def test_claude_streams_jsonl_events_with_expected_command(self):
        request = AgentRequest(
            prompt="build it",
            agent_id="claude",
            agent_name="Claude",
            workspace_path=Path("E:/workspace"),
        )
        process = _FakeProcess(
            [
                '{"type":"content_block_delta","delta":{"text":"hi"}}\n',
                '{"type":"result","result":"hi there"}\n',
            ]
        )

        with patch("app.adapters.claude_adapter.subprocess.Popen", return_value=process) as popen:
            events = list(ClaudeAdapter().stream(request))

        command = popen.call_args.args[0]
        kwargs = popen.call_args.kwargs
        self.assertEqual(
            [
                "claude",
                "-p",
                "--output-format",
                "stream-json",
                "--verbose",
                "--include-partial-messages",
                "--permission-mode",
                "plan",
                "build it",
            ],
            command,
        )
        self.assertEqual(str(Path("E:/workspace")), kwargs["cwd"])
        self.assertEqual("utf-8", kwargs["encoding"])
        self.assertEqual("replace", kwargs["errors"])
        self.assertEqual(["agent.started", "message.delta", "message.completed"], [event["type"] for event in events])

    def test_cli_errors_become_agent_failed_events(self):
        request = AgentRequest(prompt="x", agent_id="codex", agent_name="Codex")

        with patch("app.adapters.codex_adapter.subprocess.Popen", side_effect=FileNotFoundError("missing")):
            events = list(CodexAdapter().stream(request))

        self.assertEqual("agent.failed", events[-1]["type"])
        self.assertIn("missing", events[-1]["error"])

    def test_cli_start_permission_errors_become_agent_failed_events(self):
        request = AgentRequest(prompt="x", agent_id="codex", agent_name="Codex")

        with patch("app.adapters.codex_adapter.subprocess.Popen", side_effect=PermissionError("denied")):
            events = list(CodexAdapter().stream(request))

        self.assertEqual("agent.failed", events[-1]["type"])
        self.assertIn("denied", events[-1]["error"])

    def test_invalid_json_becomes_agent_failed_event(self):
        request = AgentRequest(prompt="x", agent_id="claude", agent_name="Claude")
        process = _FakeProcess(["not json\n"])

        with patch("app.adapters.claude_adapter.subprocess.Popen", return_value=process):
            events = list(ClaudeAdapter().stream(request))

        self.assertEqual("agent.failed", events[-1]["type"])
        self.assertIn("Invalid JSON", events[-1]["error"])

    def test_codex_ignores_known_trailing_non_json_cleanup_lines(self):
        request = AgentRequest(prompt="x", agent_id="codex", agent_name="Codex")
        process = _FakeProcess(
            [
                '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n',
                "SUCCESS: The process with PID 123 has been terminated.\n",
            ]
        )

        with patch("app.adapters.codex_adapter.subprocess.Popen", return_value=process):
            events = list(CodexAdapter().stream(request))

        self.assertEqual("message.completed", events[-1]["type"])
        self.assertEqual("done", events[-1]["content"])

    def test_non_zero_exit_becomes_agent_failed_event(self):
        request = AgentRequest(prompt="x", agent_id="codex", agent_name="Codex")
        process = _FakeProcess([], returncode=2, stderr="bad exit")

        with patch("app.adapters.codex_adapter.subprocess.Popen", return_value=process):
            events = list(CodexAdapter().stream(request))

        self.assertEqual("agent.failed", events[-1]["type"])
        self.assertIn("bad exit", events[-1]["error"])


if __name__ == "__main__":
    unittest.main()
