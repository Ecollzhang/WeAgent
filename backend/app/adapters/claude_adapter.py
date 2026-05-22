from app.adapters.base_adapter import BaseAgentAdapter


class ClaudeAdapter(BaseAgentAdapter):
    """Adapter for Claude AI agent.

    Currently returns mock responses. Will be connected to actual Claude API.
    """

    def send_prompt(self, prompt, context=None):
        """Send prompt to Claude and return response."""
        context = context or {}
        agent_name = context.get('agent_name', 'Claude Code')

        # Mock response based on prompt keywords
        prompt_lower = prompt.lower()

        if 'hello' in prompt_lower or 'hi' in prompt_lower or '你好' in prompt_lower:
            return f"Hello! I'm **{agent_name}**, your AI development assistant. How can I help you today?"

        if 'python' in prompt_lower or '代码' in prompt_lower:
            return (
                f"Here's a Python example you requested:\n\n"
                f"```python\n"
                f"def fibonacci(n):\n"
                f"    \"\"\"Generate Fibonacci sequence up to n terms.\"\"\"\n"
                f"    fib = [0, 1]\n"
                f"    for i in range(2, n):\n"
                f"        fib.append(fib[i-1] + fib[i-2])\n"
                f"    return fib[:n]\n\n"
                f"# Example usage\n"
                f"result = fibonacci(10)\n"
                f"print(f'Fibonacci(10): {{result}}')\n"
                f"```\n\n"
                f"This code generates the first **{10}** terms of the Fibonacci sequence. "
                f"You can adjust the parameter `n` to get more or fewer terms."
            )

        if 'vue' in prompt_lower or '前端' in prompt_lower:
            return (
                f"Here's a Vue component example:\n\n"
                f"```vue\n"
                f"<template>\n"
                f"  <div class=\"counter\">\n"
                f"    <h2>Count: {{ count }}</h2>\n"
                f"    <button @click=\"increment\">+</button>\n"
                f"    <button @click=\"decrement\">-</button>\n"
                f"  </div>\n"
                f"</template>\n\n"
                f"<script>\n"
                f"export default {\n"
                f"  data() {\n"
                f"    return { count: 0 }\n"
                f"  },\n"
                f"  methods: {\n"
                f"    increment() { this.count++ },\n"
                f"    decrement() { this.count-- }\n"
                f"  }\n"
                f"}\n"
                f"</script>\n"
                f"```\n\n"
                f"This is a simple counter component built with Vue. "
                f"It demonstrates data binding and event handling."
            )

        return (
            f"Thank you for your message! I've received your request at **{agent_name}**.\n\n"
            f"> {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n\n"
            f"I'm currently analyzing your requirements. As an AI development assistant, "
            f"I can help you with:\n"
            f"- Code generation and review\n"
            f"- Architecture design\n"
            f"- Debugging and optimization\n"
            f"- Documentation\n\n"
            f"Please let me know if you need anything specific!"
        )
