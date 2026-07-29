"""
Provider runner interfaces for sandbox agent runtimes.

The base runner defines provider-specific hooks. The generic process lifecycle
stays in AgentRuntime so Claude behavior remains stable while later providers
can reuse the same execution shell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from container.agent import AgentRuntime


class ProviderRunner:
    provider_name = "base"
    display_name = "Provider"
    log_prefix = "provider"
    started_event = "provider_started"
    stdout_delta_event = "provider_output_delta"
    stderr_delta_event = "provider_error_delta"
    output_event = "provider_output"
    error_event = "provider_error"
    stopped_event = "provider_stopped"
    timeout_env_var = "AGENT_EXEC_TIMEOUT_SECONDS"
    default_timeout_seconds = 7200

    def __init__(self, runtime: "AgentRuntime"):
        self.runtime = runtime

    def setup(self) -> None:
        """Prepare provider-specific files in the agent workspace."""

    def build_command(self, message: str, retry_with_resume: bool = True) -> tuple[list[str], bool]:
        """Build the CLI command and return (command, used_resume)."""
        raise NotImplementedError

    def environment(self) -> dict:
        """Return the provider process environment."""
        raise NotImplementedError

    def clean_output(self, stdout: str) -> str:
        return stdout.strip()

    def clean_error_output(self, stderr: str) -> str:
        return (stderr or "").strip()

    def fallback_output(self, stdout: str, stderr: str = "") -> str:
        return ""

    def stream_chunk(self, chunk: str, stream_name: str) -> str:
        return chunk

    def heartbeat_message(self, stdout_chars: int, stderr_chars: int) -> str:
        if stdout_chars or stderr_chars:
            return f"{self.display_name} still running, streamed {stdout_chars} chars"
        return f"{self.display_name} is thinking or using tools"

    def should_retry_without_resume(self, stderr: str) -> bool:
        return False

    def clear_resume_state(self) -> None:
        """Clear provider resume state after a resume failure."""

    def mark_success(self) -> None:
        """Persist provider resume state after a successful call."""

    def is_auth_error(self, output: str) -> bool:
        return False

    def auth_error_message(self, output: str) -> str:
        return f"[AuthError] {output}"

    def timeout_message(self, timeout_seconds: int) -> str:
        return f"[Error] {self.display_name} execution timed out ({timeout_seconds}s)"

    def not_found_message(self) -> str:
        return f"[Error] {self.display_name} CLI not found. Check Docker image."

    def empty_output_message(self) -> str:
        return f"[Error] No output from {self.display_name}"

    def stopped_message(self, elapsed: float) -> str:
        return f"[Stopped] 执行已停止（{elapsed:.0f}s）"

    def started_payload(self) -> dict:
        return {
            "agent_id": self.runtime.agent_id,
            "role": self.runtime.role,
            "message": f"{self.display_name} started",
        }

    def context_log_fields(self, used_resume: bool) -> dict:
        return {"use_resume": used_resume}

    def timeout_seconds(self) -> int:
        import os

        raw = os.environ.get(self.timeout_env_var) or os.environ.get("AGENT_EXEC_TIMEOUT_SECONDS")
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                pass
        return int(self.default_timeout_seconds)

    @property
    def runnable(self) -> bool:
        return True

    def unavailable_message(self) -> str:
        return f"Provider {self.provider_name} is not available."

    def tool_preflight(self, required_tools: list[str]) -> dict:
        """Verify provider-neutral text tool-loop availability."""
        available = self.runtime.bound_tool_names()
        required = sorted(set(str(item) for item in required_tools if item))
        missing = sorted(set(required) - set(available))
        return {
            "ready": self.runnable and not missing,
            "provider": self.provider_name,
            "transport": "text_tool_loop",
            "required_tools": required,
            "available_tools": available,
            "missing_tools": missing,
            "error": self.unavailable_message() if not self.runnable else "",
        }


class UnsupportedProviderRunner(ProviderRunner):
    display_name = "Unsupported Provider"
    log_prefix = "provider"

    def __init__(self, runtime: "AgentRuntime", provider_name: str):
        super().__init__(runtime)
        self.provider_name = provider_name
        self.display_name = provider_name

    @property
    def runnable(self) -> bool:
        return False

    def build_command(self, message: str, retry_with_resume: bool = True) -> tuple[list[str], bool]:
        raise RuntimeError(self.unavailable_message())

    def environment(self) -> dict:
        return {}

    def unavailable_message(self) -> str:
        return (
            f"Provider {self.provider_name} is configured for this agent, "
            "but its sandbox runner is not implemented yet."
        )
