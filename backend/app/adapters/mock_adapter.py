from app.adapters.base_adapter import BaseAgentAdapter
from app.adapters.types import make_event


class MockAdapter(BaseAgentAdapter):
    """Deterministic streaming adapter for tests and demo fallback."""

    def stream(self, request):
        content = (
            f"**{request.agent_name or 'Mock Agent'}** received your request: "
            f"{request.prompt}"
        )
        split_at = max(1, len(content) // 2)

        yield make_event("agent.started", request)
        yield make_event("message.delta", request, content=content[:split_at])
        yield make_event("message.delta", request, content=content[split_at:])
        yield make_event("message.completed", request, content=content)
