from __future__ import annotations

import os
import re
import shutil
import time

from .base import ProviderRunner
from ..claude_config import claude_env, trust_projects, write_settings
from ..logging_utils import log_agent


class ClaudeCodeRunner(ProviderRunner):
    provider_name = "claude"
    display_name = "Claude Code"
    log_prefix = "claude"
    timeout_env_var = "CLAUDE_EXEC_TIMEOUT_SECONDS"
    default_timeout_seconds = 7200

    def setup(self) -> None:
        runtime = self.runtime
        agent_dir = runtime._agent_dir
        claude_dir = os.path.join(agent_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        write_settings(
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            os.environ.get("ANTHROPIC_BASE_URL", ""),
            os.environ.get("ANTHROPIC_MODEL", ""),
        )
        trust_projects(["/workspace", agent_dir])

        agent_md_path = os.path.join(claude_dir, "agent.md")
        claude_md_path = os.path.join(agent_dir, "CLAUDE.md")
        for prompt_path in (agent_md_path, claude_md_path):
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(runtime._format_agent_md())

        settings_src = "/workspace/.claude/settings.local.json"
        settings_dst = os.path.join(claude_dir, "settings.local.json")
        if os.path.exists(settings_src) and not os.path.exists(settings_dst):
            try:
                os.symlink(settings_src, settings_dst)
            except (OSError, NotImplementedError):
                shutil.copy2(settings_src, settings_dst)

    @property
    def resume_marker(self) -> str:
        return self.runtime._claude_session_marker

    def build_command(self, message: str, retry_with_resume: bool = True) -> tuple[list[str], bool]:
        runtime = self.runtime
        full_message = f"{runtime._runtime_instruction()}\n\n用户任务：\n{message}"
        use_continue = retry_with_resume and os.path.exists(self.resume_marker)
        cmd = ["claude"]
        if use_continue:
            cmd.append("-c")
        cmd.extend([
            "-p",
            full_message,
            "--permission-mode",
            "bypassPermissions",
            "--dangerously-skip-permissions",
        ])
        return cmd, use_continue

    def environment(self) -> dict:
        runtime = self.runtime
        env = os.environ.copy()
        env.update({
            **claude_env(),
            "WEAGENT_AGENT_ID": runtime.agent_id,
            "WEAGENT_WORKSPACE_NAME": runtime.workspace_name,
        })
        return env

    def clean_output(self, stdout: str) -> str:
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        output = ansi_escape.sub("", stdout or "")
        output = re.sub(r"^>\s*", "", output, flags=re.MULTILINE)
        return output.strip()

    def should_retry_without_resume(self, stderr: str) -> bool:
        return self._should_retry_without_continue(stderr)

    def clear_resume_state(self) -> None:
        try:
            os.remove(self.resume_marker)
        except OSError:
            pass

    def mark_success(self) -> None:
        try:
            with open(self.resume_marker, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except OSError as exc:
            log_agent(
                self.runtime.agent_id,
                "claude_session_marker_failed",
                level="warning",
                role=self.runtime.role,
                error=str(exc),
            )

    def is_auth_error(self, output: str) -> bool:
        auth_error_patterns = (
            "Not logged in",
            "Please run /login",
            "Invalid API key",
            "ANTHROPIC_API_KEY",
        )
        return any(pattern in output for pattern in auth_error_patterns)

    def auth_error_message(self, output: str) -> str:
        return f"[AuthError] {output}"

    def context_log_fields(self, used_resume: bool) -> dict:
        return {
            "use_continue": used_resume,
            "marker": self.resume_marker,
        }

    @staticmethod
    def _should_retry_without_continue(stderr: str) -> bool:
        text = (stderr or "").lower()
        retry_markers = (
            "no conversation",
            "conversation not found",
            "could not continue",
            "cannot continue",
            "no previous",
            "unknown option",
            "invalid option",
        )
        return any(marker in text for marker in retry_markers)
