from abc import ABC, abstractmethod


class BaseAgentAdapter(ABC):
    """Abstract base adapter for external AI agents."""

    @abstractmethod
    def send_prompt(self, prompt, context=None):
        """Send a prompt to the AI agent and get a response.

        Args:
            prompt: The user's message/prompt
            context: Optional dict with additional context
                     (e.g., system_prompt, conversation_history, agent_name)

        Returns:
            str: The agent's response text
        """
        pass
