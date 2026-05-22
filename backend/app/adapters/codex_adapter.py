from app.adapters.base_adapter import BaseAgentAdapter


class CodexAdapter(BaseAgentAdapter):
    """Adapter for Codex AI agent.

    Currently returns mock responses. Will be connected to actual Codex API.
    """

    def send_prompt(self, prompt, context=None):
        """Send prompt to Codex and return response."""
        context = context or {}
        agent_name = context.get('agent_name', 'Codex')

        prompt_lower = prompt.lower()

        if 'hello' in prompt_lower or 'hi' in prompt_lower:
            return f"Hi! I'm **{agent_name}**, specialized in code generation and completion."

        if 'python' in prompt_lower or '代码' in prompt_lower:
            return (
                f"Here's optimized Python code for your request:\n\n"
                f"```python\n"
                f"from functools import lru_cache\n\n"
                f"@lru_cache(maxsize=None)\n"
                f"def fibonacci(n: int) -> int:\n"
                f"    \"\"\"Compute nth Fibonacci number efficiently using memoization.\"\"\"\n"
                f"    if n < 2:\n"
                f"        return n\n"
                f"    return fibonacci(n - 1) + fibonacci(n - 2)\n\n"
                f"# Generate first 20 Fibonacci numbers\n"
                f"fib_sequence = [fibonacci(i) for i in range(20)]\n"
                f"print(fib_sequence)\n"
                f"```\n\n"
                f"This implementation uses **memoization** for O(n) complexity. "
                f"The `@lru_cache` decorator automatically caches results."
            )

        return (
            f"**{agent_name}** received your request.\n\n"
            f"I'm analyzing the code requirements. I specialize in:\n"
            f"- Code completion and suggestions\n"
            f"- Multi-language support (Python, JS, TS, Go, Rust)\n"
            f"- Performance optimization\n"
            f"- Test generation\n\n"
            f"I'll prepare the best solution for you!"
        )
