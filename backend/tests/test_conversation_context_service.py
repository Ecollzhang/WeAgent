import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.services import conversation_context_service as context_module
from app.services.conversation_context_service import ConversationContextService


def _message(conversation_id, sender_type, content, minutes, sender_id=None):
    return SimpleNamespace(
        id=f"{conversation_id}-{minutes}",
        conversation_id=conversation_id,
        sender_type=sender_type,
        sender_id=sender_id or sender_type,
        content=content,
        created_at=datetime(2026, 5, 25, 12, 0, 0) + timedelta(minutes=minutes),
        artifact=None,
    )


class _FakeMessageRepo:
    def __init__(self, messages):
        self._messages = messages

    def get_all(self, **filters):
        conversation_id = filters.get("conversation_id")
        return [
            message
            for message in self._messages
            if message.conversation_id == conversation_id
        ]


class ConversationContextServiceTest(unittest.TestCase):
    def setUp(self):
        context_module.clear_recorded_context()

    def test_build_context_loads_bounded_transcript(self):
        messages = [
            _message("other", "user", "outside", 0),
            _message("conversation-1", "user", "oldest", 1),
            _message("conversation-1", "agent", "middle", 2, sender_id="agent-1"),
            _message("conversation-1", "user", "newest", 3),
        ]

        with patch.object(context_module, "message_repo", _FakeMessageRepo(messages)):
            context = ConversationContextService().build_context(
                "conversation-1",
                max_messages=2,
            )

        self.assertEqual("conversation-1", context["conversation_id"])
        self.assertEqual(
            ["middle", "newest"],
            [item["content"] for item in context["transcript"]],
        )
        self.assertEqual(
            ["agent", "user"],
            [item["sender_type"] for item in context["transcript"]],
        )
        self.assertNotIn(
            "outside",
            [item["content"] for item in context["transcript"]],
        )

    def test_record_event_captures_artifact_path(self):
        service = ConversationContextService()

        service.record_event(
            "conversation-1",
            {
                "type": "artifact.created",
                "agentId": "agent-1",
                "artifact": {
                    "title": "Plan",
                    "storagePath": "docs/plan.md",
                },
            },
        )
        context = service.build_context("conversation-1")

        self.assertEqual(
            [
                {
                    "kind": "artifact",
                    "path": "docs/plan.md",
                    "title": "Plan",
                    "source_event_type": "artifact.created",
                    "agent_id": "agent-1",
                }
            ],
            [
                {key: item[key] for key in ("kind", "path", "title", "source_event_type", "agent_id")}
                for item in context["artifact_context"]
            ],
        )

    def test_format_prompt_includes_transcript_file_context_and_current_message(self):
        context = {
            "conversation_id": "conversation-1",
            "transcript": [
                {
                    "sender_type": "user",
                    "sender_id": "user-1",
                    "content": "请读 docs/spec.md",
                    "created_at": "2026-05-25T12:00:00",
                },
                {
                    "sender_type": "agent",
                    "sender_id": "agent-1",
                    "content": "我已经读完 spec。",
                    "created_at": "2026-05-25T12:01:00",
                },
            ],
            "file_context": [
                {
                    "kind": "artifact",
                    "path": "docs/spec.md",
                    "title": "spec",
                    "source_event_type": "artifact.created",
                    "agent_id": "agent-1",
                    "created_at": "2026-05-25T12:01:00",
                }
            ],
            "artifact_context": [],
            "summary": "",
            "limits": {"max_messages": 20},
        }

        prompt = ConversationContextService().format_prompt(
            system_prompt="Be precise.",
            context=context,
            current_user_message="继续基于刚才的文件说下一步。",
        )

        self.assertIn("## Agent Instructions", prompt)
        self.assertIn("Be precise.", prompt)
        self.assertIn("## Conversation Context", prompt)
        self.assertIn("请读 docs/spec.md", prompt)
        self.assertIn("我已经读完 spec。", prompt)
        self.assertIn("## File and Artifact Context", prompt)
        self.assertIn("docs/spec.md", prompt)
        self.assertIn("## Current User Message", prompt)
        self.assertIn("继续基于刚才的文件说下一步。", prompt)


if __name__ == "__main__":
    unittest.main()
