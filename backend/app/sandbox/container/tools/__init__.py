"""
container.tools — Tool registry + built-in tools for orchestrator.

Tools are Python callables that agents can invoke.
The orchestrator intercepts tool calls and executes them.
"""

import json
import os
import re
import subprocess
from typing import Any, Callable


class ToolRegistry:
    """Registry of tools available to agents."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    TOOL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

    def register(self, name: str, fn: Callable, description: str = ""):
        if not self.TOOL_NAME_RE.match(name):
            raise ValueError(f"Invalid tool name: '{name}'. Must match {self.TOOL_NAME_RE.pattern}")
        self._tools[name] = {"fn": fn, "description": description or name}

    def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found")
        return tool["fn"](**kwargs)

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": i["description"]} for n, i in self._tools.items()]

    def call_from_agent(self, agent_id: str, tool_name: str, args: dict) -> str:
        try:
            result = self.execute(tool_name, **args)
            return json.dumps({"status": "ok", "result": result}, ensure_ascii=False)
        except Exception as e:
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
