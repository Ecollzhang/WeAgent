from __future__ import annotations

from .base import UnsupportedProviderRunner
from .claude_code import ClaudeCodeRunner
from .codex import CodexRunner
from .opencode import OpenCodeRunner


class ProviderRunnerFactory:
    _providers = {
        "claude": ClaudeCodeRunner,
        "claude_code": ClaudeCodeRunner,
        "codex": CodexRunner,
        "opencode": OpenCodeRunner,
    }

    @classmethod
    def create(cls, provider_name: str, runtime):
        key = (provider_name or "claude").strip().lower()
        runner_cls = cls._providers.get(key)
        if key not in cls._providers:
            raise ValueError(f"Unsupported provider: {provider_name}")
        if runner_cls is None:
            return UnsupportedProviderRunner(runtime, key)
        return runner_cls(runtime)

    @classmethod
    def providers(cls) -> list[str]:
        return sorted(cls._providers)
