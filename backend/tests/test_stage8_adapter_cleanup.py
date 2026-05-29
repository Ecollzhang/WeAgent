import importlib
import unittest

from marshmallow import ValidationError


class Stage8AdapterCleanupTest(unittest.TestCase):
    def test_agent_schema_rejects_mock_adapter(self):
        from app.schemas.agent_schema import CreateAgentSchema

        schema = CreateAgentSchema()
        with self.assertRaises(ValidationError):
            schema.load({"name": "Mock Agent", "adapter_name": "mock"})

        data = schema.load({"name": "Codex Agent", "adapter_name": "codex"})
        self.assertEqual("codex", data["adapter_name"])

    def test_orchestrator_service_has_no_host_adapter_factory(self):
        module = importlib.import_module("app.services.orchestrator_service")

        self.assertFalse(hasattr(module, "AgentAdapterFactory"))
        self.assertFalse(hasattr(module, "AgentRequest"))


if __name__ == "__main__":
    unittest.main()
