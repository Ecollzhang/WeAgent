import unittest
import sys
from unittest.mock import patch


def _clear_adapter_test_stubs():
    """Adapter unit tests install flask extension stubs; these tests need real DB."""
    has_stubbed_extension = False
    for module_name in (
        "flask_sqlalchemy",
        "flask_migrate",
        "flask_jwt_extended",
        "flask_cors",
        "flask_socketio",
    ):
        module = sys.modules.get(module_name)
        if module and getattr(module, "__file__", None) is None:
            has_stubbed_extension = True
            sys.modules.pop(module_name, None)

    if not has_stubbed_extension:
        return

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


class SandboxStage0BaselineTest(unittest.TestCase):
    def setUp(self):
        _clear_adapter_test_stubs()
        from app import create_app, db

        self.db = db
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db.drop_all()
        self.db.create_all()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
        self.ctx.pop()

    def _create_active_run(self):
        from app.models.agent_run import AgentRun
        from app.models.conversation import Conversation, ConversationParticipant
        from app.models.message import Message
        from app.models.user import User

        user = User(
            id="user-1",
            username="stage0",
            email="stage0@example.com",
            password_hash="x",
        )
        conversation = Conversation(
            id="conversation-1",
            owner_id="user-1",
            title="Stage 0",
            sandbox_session_id="sandbox-1",
            sandbox_status="running",
        )
        participant = ConversationParticipant(
            conversation_id="conversation-1",
            participant_type="agent",
            participant_id="agent-1",
            participant_name="Frontend Agent",
        )
        message = Message(
            id="message-1",
            conversation_id="conversation-1",
            sender_type="agent",
            sender_id="agent-1",
            content="正在处理...",
            message_type="text",
            elements=[{"type": "progress", "content": "正在处理...", "status": "running"}],
            status="streaming",
            raw_output="",
        )
        run = AgentRun(
            id="run-1",
            conversation_id="conversation-1",
            round_id="round-1",
            message_id="message-1",
            agent_id="agent-1",
            sandbox_session_id="sandbox-1",
            status="running",
        )
        self.db.session.add_all([user, conversation, participant, message, run])
        self.db.session.commit()
        return conversation, message, run

    def test_message_projection_sanitizes_private_ids_inside_progress_elements(self):
        from app.models.message import Message
        from app.services.message_service import _message_dict

        conversation, message, _ = self._create_active_run()
        conversation.kb_domain = "edu"
        message.elements = [{
            "type": "progress",
            "content": "前置任务未成功完成：edu-intent-courseware_create-2",
            "status": "failed",
            "data": {
                "content": (
                    "前置任务未成功完成：edu-intent-courseware_create-2"
                ),
            },
        }]
        self.db.session.commit()

        projected = _message_dict(Message.query.get("message-1"))

        progress = projected["elements"][0]
        self.assertNotIn("edu-intent-courseware_create-2", progress["content"])
        self.assertEqual("前置任务未成功完成：前置步骤", progress["content"])
        self.assertEqual(progress["content"], progress["data"]["content"])

    def test_sandbox_events_persist_raw_output_elements_and_meta_events(self):
        from app.models.message import Message
        from app.services.sandbox_event_bridge import sandbox_event_bridge

        self._create_active_run()

        with patch("app.services.sandbox_event_bridge.socketio.emit"):
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "claude_output_delta",
                "seq": 1,
                "data": {"chunk": "hello from claude\n"},
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "agent_report_element",
                "seq": 2,
                "data": {
                    "type": "table",
                    "content": "Feature table",
                    "status": "done",
                    "data": {
                        "title": "Feature table",
                        "headers": ["Page", "Status"],
                        "rows": [["Login", "Done"]],
                    },
                },
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "file_write",
                "seq": 3,
                "data": {
                    "file": "/workspace/agents/frontend/index.html",
                    "size": 128,
                },
            })

        self.db.session.expire_all()
        message = Message.query.get("message-1")

        self.assertEqual("hello from claude\n", message.raw_output)
        self.assertEqual("streaming", message.status)
        self.assertTrue(any(element.get("type") == "table" for element in message.elements))
        self.assertTrue(any(element.get("type") == "file" for element in message.elements))
        self.assertTrue(any(element.get("type") == "progress" for element in message.elements))

        events = (message.meta or {}).get("events") or []
        self.assertEqual(["agent_report_element", "file_write"], [event["type"] for event in events])

    def test_fallback_finalization_recovers_report_elements_from_committed_events(self):
        from app.models.message import Message
        from app.services.message_service import message_service

        self._create_active_run()
        message = Message.query.get("message-1")
        message.meta = {
            "events": [
                {
                    "type": "agent_report_element",
                    "seq": 2,
                    "data": {
                        "type": "table",
                        "content": "Knowledge search results",
                        "status": "done",
                        "data": {
                            "title": "Knowledge search results (3)",
                            "headers": ["Source", "Excerpt"],
                            "rows": [["lesson.pdf", "Della counted the money."]],
                        },
                    },
                }
            ]
        }
        message.elements = [
            {"type": "progress", "content": "Working", "status": "running"}
        ]
        self.db.session.commit()

        with patch("app.services.message_service.socketio.emit"):
            message_service._mark_agent_message_done_if_active(
                "message-1",
                "run-1",
                "agent-1",
                "Research completed",
            )

        self.db.session.expire_all()
        persisted = Message.query.get("message-1")
        self.assertTrue(
            any(element.get("type") == "table" for element in persisted.elements),
            persisted.elements,
        )

    def test_finalizer_merges_business_card_after_completion_callback_wins_race(self):
        from app.models.agent_run import AgentRun
        from app.models.message import Message
        from app.services.message_service import message_service

        self._create_active_run()
        message = Message.query.get("message-1")
        run = AgentRun.query.get("run-1")
        message.meta = {
            "events": [
                {
                    "type": "agent_report_element",
                    "seq": 2,
                    "data": {
                        "type": "table",
                        "content": "Knowledge search results",
                        "status": "done",
                        "data": {
                            "title": "Knowledge search results (3)",
                            "headers": ["Source", "Excerpt"],
                            "rows": [["lesson.pdf", "Della counted the money."]],
                        },
                    },
                }
            ]
        }
        message.elements = [
            {"type": "progress", "content": "Completed", "status": "done"},
            {"type": "text", "content": "Research completed"},
        ]
        message.status = "done"
        run.status = "done"
        self.db.session.commit()

        education_card = {
            "type": "education_card",
            "content": "Courseware draft created",
            "data": {
                "canonical_ref": {
                    "object_type": "lesson_content",
                    "object_id": "content-1",
                    "version_id": "version-1",
                }
            },
        }
        with patch("app.services.message_service.socketio.emit"):
            message_service._mark_agent_message_done_if_active(
                "message-1",
                "run-1",
                "agent-1",
                "Research completed",
                extra_elements=[education_card],
            )

        self.db.session.expire_all()
        persisted = Message.query.get("message-1")
        types = [element.get("type") for element in persisted.elements]
        self.assertIn("table", types, persisted.elements)
        self.assertIn("education_card", types, persisted.elements)

    def test_dependency_file_write_events_do_not_hide_progress_history(self):
        from app.models.message import Message
        from app.services.sandbox_event_bridge import sandbox_event_bridge

        self._create_active_run()

        with patch("app.services.sandbox_event_bridge.socketio.emit"):
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "agent_task_started",
                "seq": 1,
                "data": {"message": "start task"},
            })
            for seq in range(2, 160):
                sandbox_event_bridge.handle_event({
                    "session_id": "sandbox-1",
                    "agent_id": "agent-1",
                    "type": "file_write",
                    "seq": seq,
                    "data": {
                        "file": f"/workspace/agents/frontend/node_modules/pkg/file-{seq}.js",
                        "size": 12,
                    },
                })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "file_write",
                "seq": 200,
                "data": {
                    "file": "/workspace/agents/frontend/src/App.vue",
                    "size": 128,
                },
            })

        self.db.session.expire_all()
        message = Message.query.get("message-1")
        events = (message.meta or {}).get("events") or []
        event_types = [event["type"] for event in events]

        self.assertIn("agent_task_started", event_types)
        self.assertEqual(0, sum(
            1 for event in events
            if event["type"] == "file_write"
            and "node_modules" in event.get("data", {}).get("file", "")
        ))
        self.assertFalse(any(
            element.get("data", {}).get("path", "").find("node_modules") >= 0
            for element in message.elements
        ))
        self.assertTrue(any(
            element.get("type") == "file"
            and element.get("data", {}).get("path") == "/workspace/agents/frontend/src/App.vue"
            for element in message.elements
        ))

    def test_provider_events_persist_provider_and_remain_claude_compatible(self):
        from app.models.message import Message
        from app.services.sandbox_event_bridge import sandbox_event_bridge

        self._create_active_run()

        with patch("app.services.sandbox_event_bridge.socketio.emit"):
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "provider_started",
                "seq": 1,
                "data": {"provider": "codex", "message": "Codex started"},
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "provider_output_delta",
                "seq": 2,
                "data": {"provider": "codex", "chunk": "hello from codex\n"},
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "provider_output",
                "seq": 3,
                "data": {"provider": "codex", "output": "hello from codex\n"},
            })

        self.db.session.expire_all()
        message = Message.query.get("message-1")

        self.assertEqual("hello from codex\n", message.raw_output)
        self.assertEqual("codex", message.meta.get("provider"))
        events = (message.meta or {}).get("events") or []
        self.assertEqual(["provider_started", "provider_output"], [event["type"] for event in events])
        self.assertEqual("codex", events[-1]["provider"])

    def test_legacy_claude_events_still_work_after_provider_event_migration(self):
        from app.models.message import Message
        from app.services.sandbox_event_bridge import sandbox_event_bridge

        self._create_active_run()

        with patch("app.services.sandbox_event_bridge.socketio.emit"):
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "claude_started",
                "seq": 1,
                "data": {"message": "Claude Code started"},
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "claude_output_delta",
                "seq": 2,
                "data": {"chunk": "legacy claude\n"},
            })
            sandbox_event_bridge.handle_event({
                "session_id": "sandbox-1",
                "agent_id": "agent-1",
                "type": "claude_stopped",
                "seq": 3,
                "data": {"message": "stopped"},
            })

        self.db.session.expire_all()
        message = Message.query.get("message-1")

        self.assertEqual("legacy claude\n", message.raw_output)
        self.assertEqual("stopped", message.status)
        events = (message.meta or {}).get("events") or []
        self.assertEqual(["claude_started", "claude_stopped"], [event["type"] for event in events])

    def test_message_fetch_backfills_elements_from_saved_meta_events(self):
        from app.models.conversation import Conversation
        from app.models.message import Message
        from app.models.user import User
        from app.services.message_service import message_service

        user = User(
            id="user-1",
            username="stage0",
            email="stage0@example.com",
            password_hash="x",
        )
        conversation = Conversation(
            id="conversation-1",
            owner_id="user-1",
            title="Stage 0",
            sandbox_session_id="sandbox-1",
            sandbox_status="running",
        )
        message = Message(
            id="message-1",
            conversation_id="conversation-1",
            sender_type="agent",
            sender_id="agent-1",
            content="summary",
            message_type="text",
            elements=[
                {"type": "progress", "content": "正在处理...", "status": "running"},
                {"type": "text", "content": "summary"},
            ],
            status="done",
            raw_output="summary",
            meta={
                "events": [
                    {
                        "type": "agent_report_element",
                        "data": {
                            "type": "table",
                            "content": "Feature table",
                            "status": "done",
                            "data": {
                                "title": "Feature table",
                                "headers": ["Page", "Status"],
                                "rows": [["Login", "Done"]],
                            },
                        },
                    },
                    {
                        "type": "agent_report_element",
                        "data": {
                            "type": "file",
                            "content": "/workspace/agents/frontend/index.html",
                            "status": "done",
                            "data": {
                                "path": "/workspace/agents/frontend/index.html",
                                "name": "index.html",
                                "size": 128,
                                "title": "index.html",
                            },
                        },
                    },
                    {
                        "type": "agent_report_element",
                        "data": {
                            "type": "result",
                            "content": "All done",
                            "status": "done",
                            "data": {"title": "Done"},
                        },
                    },
                ],
            },
        )
        self.db.session.add_all([user, conversation, message])
        self.db.session.commit()

        result, error = message_service.get_conversation_messages(
            "conversation-1",
            user.id,
        )

        self.assertIsNone(error)
        elements = result["items"][0]["elements"]
        self.assertTrue(any(element.get("type") == "table" for element in elements))
        self.assertTrue(any(element.get("type") == "file" for element in elements))
        self.assertTrue(any(element.get("type") == "result" for element in elements))

        self.db.session.expire_all()
        persisted = Message.query.get("message-1")
        self.assertTrue(any(element.get("type") == "table" for element in persisted.elements))
        self.assertTrue(any(element.get("type") == "file" for element in persisted.elements))
        self.assertTrue(any(element.get("type") == "result" for element in persisted.elements))


class ClaudeCommandBaselineTest(unittest.TestCase):
    def test_claude_uses_continue_flag_when_session_marker_exists(self):
        from app.sandbox.container.agent import ClaudeRuntime

        captured = {}

        def fake_popen(command, **kwargs):
            captured["command"] = command
            raise FileNotFoundError("claude missing")

        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")

        with patch("app.sandbox.container.agent.os.path.exists", return_value=True), \
             patch("app.sandbox.container.agent.subprocess.Popen", side_effect=fake_popen), \
             patch("app.sandbox.container.agent.push_event"), \
             patch("app.sandbox.container.agent.log_agent"):
            runtime._call_claude("hello")

        self.assertEqual("claude", captured["command"][0])
        self.assertIn("-c", captured["command"])
        self.assertIn("-p", captured["command"])

    def test_claude_omits_continue_flag_without_session_marker(self):
        from app.sandbox.container.agent import ClaudeRuntime

        captured = {}

        def fake_popen(command, **kwargs):
            captured["command"] = command
            raise FileNotFoundError("claude missing")

        runtime = ClaudeRuntime("agent-1", "Frontend", "system", "frontend")

        with patch("app.sandbox.container.agent.os.path.exists", return_value=False), \
             patch("app.sandbox.container.agent.subprocess.Popen", side_effect=fake_popen), \
             patch("app.sandbox.container.agent.push_event"), \
             patch("app.sandbox.container.agent.log_agent"):
            runtime._call_claude("hello")

        self.assertEqual("claude", captured["command"][0])
        self.assertNotIn("-c", captured["command"])
        self.assertIn("-p", captured["command"])

    def test_claude_resume_failure_markers_are_protected(self):
        from app.sandbox.container.agent import ClaudeRuntime

        self.assertTrue(ClaudeRuntime._should_retry_without_continue("conversation not found"))
        self.assertTrue(ClaudeRuntime._should_retry_without_continue("could not continue"))
        self.assertFalse(ClaudeRuntime._should_retry_without_continue("ordinary stderr"))


if __name__ == "__main__":
    unittest.main()
