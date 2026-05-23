from abc import ABC, abstractmethod

from app.adapters.types import AgentRequest, resolve_workspace_path


class BaseAgentAdapter(ABC):
    """Abstract base adapter for external AI agents."""

    @abstractmethod
    def stream(self, request):
        """Yield normalized agent events for the request."""

    def send_prompt(self, prompt, context=None):
        """Compatibility helper that aggregates streamed message text."""
        context = context or {}
        request = AgentRequest(
            prompt=prompt,
            conversation_id=context.get("conversation_id"),
            agent_id=context.get("agent_id"),
            agent_name=context.get("agent_name"),
            system_prompt=context.get("system_prompt"),
            conversation_history=context.get("conversation_history"),
            workspace_path=context.get("workspace_path") or resolve_workspace_path(),
        )

        deltas = []
        completed = None
        for event in self.stream(request):
            event_type = event.get("type")
            if event_type == "message.delta":
                deltas.append(event.get("content", ""))
            elif event_type == "message.completed":
                completed = event.get("content")

        return completed if completed is not None else "".join(deltas)
