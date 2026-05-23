from app.adapters.base_adapter import BaseAgentAdapter
from app.adapters.types import make_event


class OpenCodeAdapter(BaseAgentAdapter):
    """Adapter for OpenCode AI agent.

    Currently returns mock responses. Will be connected to actual OpenCode API.
    """

    def stream(self, request):
        content = self.send_prompt(
            request.prompt,
            {"agent_name": request.agent_name or "OpenCode"},
        )
        yield make_event("agent.started", request)
        yield make_event("message.delta", request, content=content, text=content)
        yield make_event("message.completed", request, content=content, finalText=content)

    def send_prompt(self, prompt, context=None):
        """Send prompt to OpenCode and return response."""
        context = context or {}
        agent_name = context.get('agent_name', 'OpenCode')

        prompt_lower = prompt.lower()

        if 'hello' in prompt_lower or 'hi' in prompt_lower:
            return f"Hey there! **{agent_name}** here, ready to help with open-source development!"

        if 'review' in prompt_lower or '代码审查' in prompt_lower:
            return (
                f"## Code Review Results\n\n"
                f"I've reviewed the code and found the following:\n\n"
                f"### ✅ Good Practices\n"
                f"- Clear variable naming conventions\n"
                f"- Proper error handling structure\n\n"
                f"### ⚠️ Suggestions\n"
                f"1. **Add type hints** for better code documentation\n"
                f"2. **Consider adding unit tests** for edge cases\n"
                f"3. **Extract magic numbers** into named constants\n\n"
                f"### 📊 Overall Score: **8/10**\n"
                f"Solid implementation with minor improvements suggested."
            )

        if 'doc' in prompt_lower or '文档' in prompt_lower:
            return (
                f"## Documentation Generated\n\n"
                f"```markdown\n"
                f"# Project Documentation\n\n"
                f"## Overview\n"
                f"This project provides a multi-agent collaboration platform.\n\n"
                f"## Installation\n"
                f"```bash\n"
                f"pip install -r requirements.txt\n"
                f"npm install\n"
                f"```\n\n"
                f"## Usage\n"
                f"1. Start the backend: `python run.py`\n"
                f"2. Start the frontend: `npm run serve`\n"
                f"3. Open http://localhost:8080\n"
                f"```\n\n"
                f"I've generated comprehensive documentation for your project."
            )

        return (
            f"**{agent_name}** is on it!\n\n"
            f"I specialize in:\n"
            f"- Open-source project management\n"
            f"- Code review and quality analysis\n"
            f"- Documentation generation\n"
            f"- Dependency management\n\n"
            f"Let me work on your request and get back to you with the best solution."
        )
