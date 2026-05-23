import json
import subprocess

from app.adapters.base_adapter import BaseAgentAdapter
from app.adapters.normalizers import normalize_claude_event
from app.adapters.types import make_event, resolve_workspace_path


class ClaudeAdapter(BaseAgentAdapter):
    """Adapter for Claude Code CLI stream-json output."""

    def stream(self, request):
        workspace_path = request.workspace_path or resolve_workspace_path()
        command = [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            "--permission-mode",
            "plan",
            request.prompt,
        ]

        yield make_event("agent.started", request)
        try:
            process = subprocess.Popen(
                command,
                cwd=str(workspace_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
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
                yield make_event(
                    "agent.failed",
                    request,
                    error=f"Invalid JSON from Claude CLI: {exc}",
                )
                return

            for event in normalize_claude_event(raw_event, request):
                yield event

        return_code = process.wait()
        if return_code:
            stderr = process.stderr.read() if process.stderr else ""
            yield make_event(
                "agent.failed",
                request,
                error=stderr or f"Claude CLI exited with code {return_code}",
            )
