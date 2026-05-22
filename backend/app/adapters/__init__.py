from app.adapters.claude_adapter import ClaudeAdapter
from app.adapters.codex_adapter import CodexAdapter
from app.adapters.opencode_adapter import OpenCodeAdapter


ADAPTER_MAP = {
    'claude': ClaudeAdapter,
    'codex': CodexAdapter,
    'opencode': OpenCodeAdapter,
}


def get_adapter(adapter_name):
    """Get adapter class by name."""
    adapter_class = ADAPTER_MAP.get(adapter_name.lower())
    if not adapter_class:
        raise ValueError(f'Unknown adapter: {adapter_name}')
    return adapter_class
