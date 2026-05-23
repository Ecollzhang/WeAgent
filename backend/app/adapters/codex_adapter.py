import json
import os
import shutil
import subprocess

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
            )
        except OSError as exc:
            yield make_event("agent.failed", request, error=str(exc))
            return

        yield from self._stream_process_events(process, request)

    def _stream_process_events(self, process, request):
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
        if return_code:
            stderr = process.stderr.read() if process.stderr else ""
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


def _is_ignorable_non_json_line(line):
    return line.startswith("SUCCESS: The process with PID")
