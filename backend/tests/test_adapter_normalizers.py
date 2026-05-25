import unittest

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.adapters.normalizers import normalize_claude_event, normalize_codex_event
from app.adapters.types import AgentRequest


class AdapterNormalizerTest(unittest.TestCase):
    def setUp(self):
        self.request = AgentRequest(
            prompt="build a page",
            conversation_id="conversation-1",
            agent_id="codex",
            agent_name="Codex",
        )

    def test_codex_normalizes_text_and_completion_events(self):
        delta_events = normalize_codex_event(
            {"type": "message_delta", "delta": "hello"}, self.request
        )
        completed_events = normalize_codex_event(
            {"type": "message_completed", "content": "hello world"}, self.request
        )
        item_completed_events = normalize_codex_event(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "from codex"},
            },
            self.request,
        )

        self.assertEqual("message.delta", delta_events[0]["type"])
        self.assertEqual("hello", delta_events[0]["content"])
        self.assertEqual("hello", delta_events[0]["text"])
        self.assertEqual("message.completed", completed_events[0]["type"])
        self.assertEqual("hello world", completed_events[0]["content"])
        self.assertEqual("hello world", completed_events[0]["finalText"])
        self.assertEqual("message.completed", item_completed_events[0]["type"])
        self.assertEqual("from codex", item_completed_events[0]["content"])

    def test_codex_normalizes_tools_artifacts_and_errors(self):
        started = normalize_codex_event(
            {
                "type": "tool_call",
                "status": "started",
                "name": "shell",
                "input": {"command": "ls"},
            },
            self.request,
        )
        completed = normalize_codex_event(
            {"type": "tool_result", "name": "shell", "output": {"exit_code": 0}},
            self.request,
        )
        artifact = normalize_codex_event(
            {"type": "artifact", "path": "src/App.vue", "title": "App.vue"},
            self.request,
        )
        failed = normalize_codex_event(
            {"type": "error", "message": "CLI failed"}, self.request
        )

        self.assertEqual("tool.started", started[0]["type"])
        self.assertEqual("shell", started[0]["toolName"])
        self.assertEqual("tool.completed", completed[0]["type"])
        self.assertEqual("artifact.created", artifact[0]["type"])
        self.assertEqual("src/App.vue", artifact[0]["artifact"]["storagePath"])
        self.assertEqual("agent.failed", failed[0]["type"])
        self.assertEqual("CLI failed", failed[0]["error"])

    def test_codex_reconnecting_errors_are_status_events(self):
        events = normalize_codex_event(
            {"type": "error", "message": "Reconnecting... 2/5 (timeout waiting for child process to exit)"},
            self.request,
        )

        self.assertEqual("agent.status", events[0]["type"])
        self.assertEqual("reconnecting", events[0]["status"])

    def test_claude_normalizes_partial_text_result_tools_and_errors(self):
        delta = normalize_claude_event(
            {"type": "content_block_delta", "delta": {"text": "hi"}}, self.request
        )
        completed = normalize_claude_event(
            {"type": "result", "result": "final answer"}, self.request
        )
        tool_started = normalize_claude_event(
            {
                "type": "content_block_start",
                "content_block": {"type": "tool_use", "name": "Read", "input": {}},
            },
            self.request,
        )
        tool_completed = normalize_claude_event(
            {
                "type": "content_block_stop",
                "content_block": {
                    "type": "tool_result",
                    "name": "Read",
                    "content": "ok",
                },
            },
            self.request,
        )
        failed = normalize_claude_event(
            {"type": "error", "error": {"message": "denied"}}, self.request
        )

        self.assertEqual("message.delta", delta[0]["type"])
        self.assertEqual("hi", delta[0]["content"])
        self.assertEqual("message.completed", completed[0]["type"])
        self.assertEqual("final answer", completed[0]["content"])
        self.assertEqual("tool.started", tool_started[0]["type"])
        self.assertEqual("Read", tool_started[0]["toolName"])
        self.assertEqual("tool.completed", tool_completed[0]["type"])
        self.assertEqual("agent.failed", failed[0]["type"])
        self.assertEqual("denied", failed[0]["error"])

    def test_unknown_raw_events_are_ignored(self):
        self.assertEqual([], normalize_codex_event({"type": "session_info"}, self.request))
        self.assertEqual([], normalize_claude_event({"type": "system"}, self.request))


if __name__ == "__main__":
    unittest.main()
