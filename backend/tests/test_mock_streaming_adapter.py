import unittest

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.adapters.mock_adapter import MockAdapter
from app.adapters.types import AgentRequest


class MockStreamingAdapterTest(unittest.TestCase):
    def test_mock_adapter_streams_deterministic_message_events(self):
        request = AgentRequest(
            prompt="please respond",
            conversation_id="conversation-1",
            agent_id=42,
            agent_name="Mock Agent",
        )

        events = list(MockAdapter().stream(request))

        self.assertEqual("agent.started", events[0]["type"])
        self.assertEqual("message.completed", events[-1]["type"])
        self.assertGreaterEqual(
            len([event for event in events if event["type"] == "message.delta"]),
            2,
        )

        delta_text = "".join(
            event["content"] for event in events if event["type"] == "message.delta"
        )
        self.assertEqual(delta_text, events[-1]["content"])
        self.assertTrue(all(event["runId"] == request.run_id for event in events))


if __name__ == "__main__":
    unittest.main()
