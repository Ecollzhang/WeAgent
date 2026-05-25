import json
import os
import shutil
import subprocess
import threading

from app.adapters.base_adapter import BaseAgentAdapter
from app.adapters.normalizers import normalize_codex_event
from app.adapters.types import make_event, resolve_workspace_path


class CodexAdapter(BaseAgentAdapter):
    """Adapter for Codex CLI JSONL streaming."""

    def stream(self, request):
        workspace_path = request.workspace_path or resolve_workspace_path()
        command = [
            _codex_executable(),
            "exec",
            "--json",
            "--ephemeral",
            "--cd",
            str(workspace_path),
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            request.prompt,
        ]

        yield make_event("agent.started", request)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_codex_environment(),
            )
        except OSError as exc:
            yield make_event("agent.failed", request, error=str(exc))
            return

        yield from self._stream_process_events(process, request)

    def _stream_process_events(self, process, request):
        stderr_lines = []
        stderr_thread = _start_stderr_collector(process.stderr, stderr_lines)

        for line in process.stdout or []:
            line = line.strip()
            if not line:
                continue
            try:
                raw_event = json.loads(line)
            except json.JSONDecodeError as exc:
                if _is_ignorable_non_json_line(line):
                    continue
                yield make_event(
                    "agent.failed",
                    request,
                    error=f"Invalid JSON from Codex CLI: {exc}",
                )
                return

            for event in normalize_codex_event(raw_event, request):
                yield event

        return_code = process.wait()
        if stderr_thread:
            stderr_thread.join(timeout=1)
        if return_code:
            stderr = "".join(stderr_lines)
            yield make_event(
                "agent.failed",
                request,
                error=stderr or f"Codex CLI exited with code {return_code}",
            )


def _codex_executable():
    if os.name == "nt":
        return (
            shutil.which("codex.cmd")
            or shutil.which("codex.exe")
            or shutil.which("codex")
            or "codex"
        )
    return shutil.which("codex") or "codex"


def _codex_environment():
    env = os.environ.copy()
    codex_home = os.getenv("WEAGENT_CODEX_HOME")
    if codex_home:
        env["CODEX_HOME"] = codex_home
    return env


def _start_stderr_collector(stderr, stderr_lines):
    if not stderr:
        return None

    thread = threading.Thread(
        target=_collect_stderr,
        args=(stderr, stderr_lines),
        daemon=True,
    )
    thread.start()
    return thread


def _collect_stderr(stderr, stderr_lines):
    try:
        text = stderr.read()
    except Exception as exc:  # pragma: no cover - defensive guard for stream implementations.
        stderr_lines.append(str(exc))
        return
    if text:
        stderr_lines.append(text)


def _is_ignorable_non_json_line(line):
    return line.startswith("SUCCESS: The process with PID")
