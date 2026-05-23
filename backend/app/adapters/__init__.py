from app.adapters.claude_adapter import ClaudeAdapter
from app.adapters.codex_adapter import CodexAdapter
from app.adapters.factory import AgentAdapterFactory
from app.adapters.mock_adapter import MockAdapter
from app.adapters.opencode_adapter import OpenCodeAdapter


AgentAdapterFactory.register("mock", MockAdapter)
AgentAdapterFactory.register("claude", ClaudeAdapter)
AgentAdapterFactory.register("codex", CodexAdapter)
AgentAdapterFactory.register("opencode", OpenCodeAdapter)


def get_adapter(adapter_name):
    """Get adapter class by name."""
    return AgentAdapterFactory.get(adapter_name)
