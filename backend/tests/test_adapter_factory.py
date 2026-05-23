import os
import unittest
from pathlib import Path

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.adapters import get_adapter
from app.adapters.base_adapter import BaseAgentAdapter
from app.adapters.factory import AgentAdapterFactory
from app.adapters.mock_adapter import MockAdapter
from app.adapters.types import AgentRequest, make_event, resolve_workspace_path


class AdapterFactoryTest(unittest.TestCase):
    def test_make_event_adds_request_metadata(self):
        request = AgentRequest(
            prompt="hello",
            conversation_id="conversation-1",
            agent_id=7,
            agent_name="Mock",
        )

        event = make_event("message.delta", request, content="hello back")

        self.assertEqual("message.delta", event["type"])
        self.assertEqual(request.run_id, event["runId"])
        self.assertEqual("conversation-1", event["conversationId"])
        self.assertEqual(7, event["agentId"])
        self.assertEqual("hello back", event["content"])
        self.assertIn("timestamp", event)

    def test_resolve_workspace_uses_env_before_project_root(self):
        previous = os.environ.get("AGENT_WORKSPACE_ROOT")
        try:
            backend_dir = Path(__file__).resolve().parents[1]
            os.environ["AGENT_WORKSPACE_ROOT"] = str(backend_dir)
            self.assertEqual(backend_dir, Path(resolve_workspace_path()))

            os.environ.pop("AGENT_WORKSPACE_ROOT", None)
            fallback = Path(resolve_workspace_path())

            self.assertEqual("WeAgent", fallback.name)
            self.assertTrue((fallback / "backend").exists())
        finally:
            if previous is None:
                os.environ.pop("AGENT_WORKSPACE_ROOT", None)
            else:
                os.environ["AGENT_WORKSPACE_ROOT"] = previous

    def test_base_send_prompt_aggregates_streaming_deltas(self):
        class EchoAdapter(BaseAgentAdapter):
            def stream(self, request):
                yield make_event("agent.started", request)
                yield make_event("message.delta", request, content="hel")
                yield make_event("message.delta", request, content="lo")
                yield make_event("message.completed", request, content="hello")

        self.assertEqual(
            "hello",
            EchoAdapter().send_prompt("ignored", {"agent_name": "Echo"}),
        )

    def test_factory_creates_registered_mock_adapter(self):
        adapter = AgentAdapterFactory.create("mock")

        self.assertIsInstance(adapter, MockAdapter)
        self.assertIn("mock", AgentAdapterFactory.providers())

    def test_get_adapter_compatibility_returns_registered_class(self):
        self.assertIs(get_adapter("mock"), MockAdapter)


if __name__ == "__main__":
    unittest.main()
