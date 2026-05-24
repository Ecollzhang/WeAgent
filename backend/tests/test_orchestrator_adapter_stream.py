import importlib.util
import unittest
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from test_support import stub_flask_extensions

stub_flask_extensions()

from app.adapters.types import make_event


def _load_orchestrator_module_with_stubs():
    dependencies = {
        "app.repositories.conversation_repo": "conversation_repo",
        "app.repositories.message_repo": "message_repo",
        "app.repositories.agent_repo": "agent_repo",
    }
    module_names = list(dependencies) + ["app.services.message_service"]
    originals = {name: sys.modules.get(name) for name in module_names}

    for module_name, attribute_name in dependencies.items():
        module = types.ModuleType(module_name)
        setattr(module, attribute_name, SimpleNamespace())
        sys.modules[module_name] = module

    message_service_module = types.ModuleType("app.services.message_service")
    message_service_module.message_service = SimpleNamespace()
    message_service_module.broadcast = lambda *args, **kwargs: None
    sys.modules["app.services.message_service"] = message_service_module

    module_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "orchestrator_service.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_orchestrator_service_under_test",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for module_name, original in originals.items():
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original
    return module


orchestrator_module = _load_orchestrator_module_with_stubs()


class _FakeAdapter:
    def __init__(self):
        self.requests = []

    def stream(self, request):
        self.requests.append(request)
        yield make_event("agent.started", request)
        yield make_event("message.delta", request, content="hel")
        yield make_event("message.delta", request, content="lo")
        yield make_event("message.completed", request, content="hello")


class _FakeMessageService:
    def __init__(self):
        self.sent = []

    def send_message(self, **kwargs):
        self.sent.append(kwargs)
        return {
            "id": "saved-message-1",
            "conversation_id": kwargs["conversation_id"],
            "sender_type": kwargs["sender_type"],
            "sender_id": kwargs["sender_id"],
            "content": kwargs["content"],
        }, None


class _FakeApp:
    def __init__(self):
        self.entered = False

    def app_context(self):
        return self

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        return False


class OrchestratorAdapterStreamTest(unittest.TestCase):
    def test_invoke_agent_streams_via_factory_and_persists_completed_text(self):
        adapter = _FakeAdapter()
        fake_message_service = _FakeMessageService()
        broadcasts = []

        original_factory = orchestrator_module.AgentAdapterFactory
        original_message_service = orchestrator_module.message_service
        original_broadcast = orchestrator_module.broadcast

        class _Factory:
            @staticmethod
            def create(provider):
                self.assertEqual("mock", provider)
                return adapter

        try:
            orchestrator_module.AgentAdapterFactory = _Factory
            orchestrator_module.message_service = fake_message_service
            orchestrator_module.broadcast = lambda conversation_id, event: broadcasts.append(
                (conversation_id, event)
            )

            agent = SimpleNamespace(
                id="agent-1",
                name="Mock Agent",
                adapter_name="mock",
                system_prompt="Be brief.",
            )

            orchestrator_module.OrchestratorService()._invoke_agent(
                agent,
                "conversation-1",
                "Say hello",
            )

            self.assertEqual(1, len(adapter.requests))
            request = adapter.requests[0]
            self.assertEqual("Say hello", request.prompt)
            self.assertEqual("conversation-1", request.conversation_id)
            self.assertEqual("agent-1", request.agent_id)
            self.assertEqual("Mock Agent", request.agent_name)
            self.assertEqual("Be brief.", request.system_prompt)

            broadcast_types = [event["type"] for _, event in broadcasts]
            self.assertEqual(
                ["agent.started", "message.delta", "message.delta", "message.completed"],
                broadcast_types,
            )
            self.assertTrue(all(item[0] == "conversation-1" for item in broadcasts))

            self.assertEqual(
                [
                    {
                        "conversation_id": "conversation-1",
                        "sender_type": "agent",
                        "sender_id": "agent-1",
                        "content": "hello",
                        "message_type": "text",
                    }
                ],
                fake_message_service.sent,
            )
        finally:
            orchestrator_module.AgentAdapterFactory = original_factory
            orchestrator_module.message_service = original_message_service
            orchestrator_module.broadcast = original_broadcast

    def test_invoke_agent_in_context_wraps_worker_with_flask_app_context(self):
        service = orchestrator_module.OrchestratorService()
        app = _FakeApp()
        calls = []

        service._invoke_agent = lambda *args: calls.append(args)
        agent = SimpleNamespace(id="agent-1")

        service._invoke_agent_in_context(app, agent, "conversation-1", "hello")

        self.assertTrue(app.entered)
        self.assertEqual([(agent, "conversation-1", "hello")], calls)


if __name__ == "__main__":
    unittest.main()
