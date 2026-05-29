"""
container.tools — Tool registry + built-in tools for orchestrator.

Tools are Python callables that agents can invoke.
The orchestrator intercepts tool calls and executes them.
"""

import json
import os
import subprocess
from typing import Any, Callable

from ..capabilities import (
    append_tool_call_record,
    now_iso,
    permissions_for_tool,
    resolve_bound_tool_capability,
    summarize_tool_input,
    summarize_tool_output,
)


class ToolRegistry:
    """Registry of tools available to agents."""

    def __init__(self, workspace_root: str = "/workspace"):
        self._tools: dict[str, dict] = {}
        self.workspace_root = os.path.realpath(workspace_root)

    def register(self, name: str, fn: Callable, description: str = ""):
        self._tools[name] = {"fn": fn, "description": description or name}

    def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found")
        global WORKSPACE_ROOT
        previous_root = WORKSPACE_ROOT
        WORKSPACE_ROOT = self.workspace_root
        try:
            return tool["fn"](**kwargs)
        finally:
            WORKSPACE_ROOT = previous_root

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": i["description"]} for n, i in self._tools.items()]

    def call_from_agent(self, agent_id: str, tool_name: str, args: dict,
                        run_id: str = None, session_id: str = None) -> str:
        started_at = now_iso()
        tool_capability = resolve_bound_tool_capability(
            agent_id,
            tool_name,
            workspace_root=self.workspace_root,
        )
        permissions_used = permissions_for_tool(tool_name)

        def _record(status: str, result=None, error: str = None):
            if not tool_capability or not run_id:
                return
            append_tool_call_record(
                {
                    "session_id": session_id or "",
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "capability_id": tool_capability.get("capability_id"),
                    "capability_version_id": tool_capability.get("capability_version_id"),
                    "call_type": "tool",
                    "tool_name": tool_name,
                    "permissions_used": permissions_used,
                    "input_summary": summarize_tool_input(tool_name, args or {}),
                    "output_summary": summarize_tool_output(result) if error is None else {},
                    "status": status,
                    "error": error,
                    "started_at": started_at,
                    "completed_at": now_iso(),
                },
                workspace_root=self.workspace_root,
            )

        try:
            if tool_capability:
                granted = set(tool_capability.get("granted_permissions") or [])
                missing = sorted(set(permissions_used) - granted)
                if missing:
                    raise PermissionError(
                        f"Missing granted permissions for {tool_name}: {', '.join(missing)}"
                    )
            result = self.execute(tool_name, **args)
            _record("completed", result=result)
            return json.dumps({"status": "ok", "result": result}, ensure_ascii=False)
        except Exception as e:
            _record("failed", error=str(e))
            return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ===== Built-in tool implementations =====

WORKSPACE_ROOT = os.path.realpath("/workspace")


def _resolve_workspace_path(path: str) -> str:
    full = os.path.join(WORKSPACE_ROOT, path.lstrip("/"))
    real = os.path.realpath(full)
    if real != WORKSPACE_ROOT and not real.startswith(WORKSPACE_ROOT + os.sep):
        raise ValueError("Access denied: path outside workspace")
    return real


def _read_file(path: str) -> str:
    full = _resolve_workspace_path(path)
    if not os.path.exists(full):
        return f"File not found: {path}"
    with open(full) as f:
        return f.read()


def _write_file(path: str, content: str) -> str:
    full = _resolve_workspace_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    return f"Written: {path}"


def _run_command(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60, cwd="/workspace")
    out = result.stdout
    if result.stderr:
        out += f"\n[stderr]\n{result.stderr}"
    return out


def _report_progress(agent_id: str, progress: str, status: str) -> str:
    import json as _json
    data = _json.dumps({"agent_id": agent_id, "progress": progress, "status": status})
    os.makedirs("/workspace/.session", exist_ok=True)
    with open(f"/workspace/.session/progress_{agent_id}.json", "w") as f:
        f.write(data)
    return f"Progress: {progress} - {status}"


def _list_files(path: str = "") -> str:
    full = os.path.join("/workspace", path.lstrip("/"))
    if not os.path.exists(full):
        return f"Path not found: {path}"
    lines = []
    for root, dirs, files in os.walk(full):
        rel = os.path.relpath(root, "/workspace")
        if rel == ".":
            rel = ""
        for f in files:
            lines.append(os.path.join(rel, f))
    return "\n".join(lines) if lines else "(empty)"


def register_builtin_tools(registry: ToolRegistry):
    """Register all built-in tools."""
    registry.register("read_file", _read_file, "Read a file from workspace")
    registry.register("write_file", _write_file, "Write content to a file")
    registry.register("run_command", _run_command, "Run a shell command")
    registry.register("report_progress", _report_progress, "Report execution progress")
    registry.register("list_files", _list_files, "List files in workspace")
