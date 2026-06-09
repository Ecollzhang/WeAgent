"""Minimal sandbox-side MCP stdio runtime.

This runtime intentionally stays small: it starts a manifest-declared command
inside the workspace, speaks JSON-RPC over stdio, and writes audited MCP tool
calls to the same .weagent run JSONL used by built-in tools.
"""

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .capabilities import (
    _safe_segment,
    append_tool_call_record,
    now_iso,
    resolve_bound_mcp_capability,
    summarize_mcp_input,
    summarize_mcp_output,
)


DEFAULT_WORKSPACE_ROOT = "/workspace"


@dataclass
class _McpServer:
    runtime_id: str
    process: subprocess.Popen
    stdout_queue: queue.Queue = field(default_factory=queue.Queue)
    stderr_lines: list[str] = field(default_factory=list)


class McpRuntime:
    """Start and call manifest-backed MCP servers inside a sandbox workspace."""

    def __init__(self, workspace_root: str = DEFAULT_WORKSPACE_ROOT,
                 request_timeout: float = 90):
        self.workspace_root = workspace_root
        self.request_timeout = request_timeout
        self._servers: dict[str, _McpServer] = {}
        self._request_counter = 0

    def list_running_servers(self) -> list[str]:
        self._cleanup_exited()
        return sorted(self._servers.keys())

    def start_server(self, agent_id: str, runtime_id: str) -> dict:
        capability, error = self._authorized_mcp(agent_id, runtime_id)
        if error:
            return {"status": "error", "error": error}
        if runtime_id in self._servers and self._servers[runtime_id].process.poll() is None:
            return {"status": "ok", "runtime_id": runtime_id, "already_running": True}

        manifest, error = self._load_manifest(runtime_id)
        if error:
            return {"status": "error", "error": error}
        command, args, error = self._entry_command(manifest)
        if error:
            return {"status": "error", "error": error}

        try:
            process = subprocess.Popen(
                [command, *args],
                cwd=self.workspace_root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except Exception as exc:
            return {"status": "error", "error": f"Failed to start MCP server: {exc}"}

        server = _McpServer(runtime_id=runtime_id, process=process)
        self._servers[runtime_id] = server
        self._start_reader_threads(server)

        try:
            initialized = self._send_request(runtime_id, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "weagent-sandbox",
                    "version": "0.1.0",
                },
            })
            self._send_notification(runtime_id, "notifications/initialized", {})
        except Exception as exc:
            self.stop_server(runtime_id)
            return {"status": "error", "error": f"MCP initialize failed: {exc}"}

        return {
            "status": "ok",
            "runtime_id": runtime_id,
            "capability_id": capability.get("capability_id"),
            "capability_version_id": capability.get("capability_version_id"),
            "initialize": initialized,
        }

    def list_tools(self, runtime_id: str) -> dict:
        if not self._is_running(runtime_id):
            return {"status": "error", "error": f"MCP server not running: {runtime_id}"}
        try:
            result = self._send_request(runtime_id, "tools/list", {})
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {
            "status": "ok",
            "runtime_id": runtime_id,
            "tools": result.get("tools") or [],
        }

    def call_tool(self, agent_id: str, runtime_id: str, tool_name: str, args: dict,
                  run_id: Optional[str] = None, session_id: str = "") -> dict:
        capability, error = self._authorized_mcp(agent_id, runtime_id)
        if error:
            self._append_call_record(
                agent_id=agent_id,
                capability=capability or {},
                runtime_id=runtime_id,
                tool_name=tool_name,
                args=args,
                run_id=run_id,
                session_id=session_id,
                started_at=now_iso(),
                status="failed",
                error=error,
            )
            return {"status": "error", "error": error}
        if not self._is_running(runtime_id):
            start = self.start_server(agent_id, runtime_id)
            if start.get("status") != "ok":
                return start

        started_at = now_iso()
        try:
            result = self._send_request(
                runtime_id,
                "tools/call",
                {"name": tool_name, "arguments": args or {}},
            )
            self._append_call_record(
                agent_id=agent_id,
                capability=capability,
                runtime_id=runtime_id,
                tool_name=tool_name,
                args=args,
                result=result,
                run_id=run_id,
                session_id=session_id,
                started_at=started_at,
                status="completed",
            )
            return {
                "status": "ok",
                "runtime_id": runtime_id,
                "tool_name": tool_name,
                "result": result,
            }
        except Exception as exc:
            error_text = str(exc)
            self._append_call_record(
                agent_id=agent_id,
                capability=capability,
                runtime_id=runtime_id,
                tool_name=tool_name,
                args=args,
                run_id=run_id,
                session_id=session_id,
                started_at=started_at,
                status="failed",
                error=error_text,
            )
            return {"status": "error", "error": error_text}

    def stop_server(self, runtime_id: str) -> dict:
        server = self._servers.pop(runtime_id, None)
        if not server:
            return {"status": "ok", "runtime_id": runtime_id, "stopped": False}
        process = server.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        return {"status": "ok", "runtime_id": runtime_id, "stopped": True}

    def stop_all(self) -> dict:
        stopped = []
        for runtime_id in list(self._servers.keys()):
            self.stop_server(runtime_id)
            stopped.append(runtime_id)
        return {"status": "ok", "stopped": stopped}

    def _authorized_mcp(self, agent_id: str, runtime_id: str) -> tuple[Optional[dict], Optional[str]]:
        capability = resolve_bound_mcp_capability(
            agent_id,
            runtime_id,
            workspace_root=self.workspace_root,
        )
        if not capability:
            return None, f"MCP capability is not bound to agent: {runtime_id}"

        manifest, error = self._load_manifest(runtime_id)
        if error:
            return capability, error
        required = self._required_permissions(manifest)
        granted = set(capability.get("granted_permissions") or [])
        missing = [permission for permission in required if permission not in granted]
        if missing:
            return capability, f"Missing granted permissions: {', '.join(missing)}"
        return capability, None

    def _required_permissions(self, envelope: dict) -> list[str]:
        permissions = envelope.get("permissions") or {}
        required = list(dict.fromkeys(permissions.get("required") or []))
        manifest = envelope.get("manifest") or {}
        entry = manifest.get("entry") or (manifest.get("raw") or {}).get("entry") or {}
        if entry.get("command") and "run_command" not in required:
            required.insert(0, "run_command")
        return required

    def _load_manifest(self, runtime_id: str) -> tuple[Optional[dict], Optional[str]]:
        path = os.path.join(
            self.workspace_root,
            ".weagent",
            "mcp",
            _safe_segment(runtime_id),
            "manifest.json",
        )
        if not os.path.exists(path):
            return None, f"MCP manifest not found: {runtime_id}"
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle), None
        except Exception as exc:
            return None, f"Failed to read MCP manifest: {exc}"

    def _entry_command(self, envelope: dict) -> tuple[Optional[str], list[str], Optional[str]]:
        manifest = envelope.get("manifest") or {}
        entry = manifest.get("entry") or (manifest.get("raw") or {}).get("entry") or {}
        command = entry.get("command")
        args = entry.get("args") or []
        if not command:
            return None, [], "MCP manifest entry.command is required"
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            return None, [], "MCP manifest entry.args must be a list of strings"
        return command, args, None

    def _start_reader_threads(self, server: _McpServer):
        def _stdout_reader():
            for line in iter(server.process.stdout.readline, ""):
                server.stdout_queue.put(line)

        def _stderr_reader():
            for line in iter(server.process.stderr.readline, ""):
                server.stderr_lines.append(line.rstrip("\n"))

        threading.Thread(target=_stdout_reader, daemon=True).start()
        threading.Thread(target=_stderr_reader, daemon=True).start()

    def _send_request(self, runtime_id: str, method: str, params: dict):
        server = self._servers.get(runtime_id)
        if not server or server.process.poll() is not None:
            raise RuntimeError(f"MCP server not running: {runtime_id}")
        if not server.process.stdin:
            raise RuntimeError("MCP server stdin is closed")

        self._request_counter += 1
        request_id = self._request_counter
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        server.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        server.process.stdin.flush()

        deadline = time.time() + self.request_timeout
        while time.time() < deadline:
            if server.process.poll() is not None:
                stderr = "\n".join(server.stderr_lines[-20:])
                raise RuntimeError(
                    f"MCP server exited with code {server.process.returncode}: {stderr}"
                )
            remaining = max(0.05, deadline - time.time())
            try:
                line = server.stdout_queue.get(timeout=min(0.2, remaining))
            except queue.Empty:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                continue
            if response.get("id") != request_id:
                continue
            if response.get("error"):
                error = response["error"]
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise RuntimeError(message)
            return response.get("result") or {}

        stderr = "\n".join(server.stderr_lines[-20:])
        raise TimeoutError(f"MCP request timed out: {method}. stderr: {stderr}")

    def _send_notification(self, runtime_id: str, method: str, params: dict):
        server = self._servers.get(runtime_id)
        if not server or server.process.poll() is not None:
            raise RuntimeError(f"MCP server not running: {runtime_id}")
        if not server.process.stdin:
            raise RuntimeError("MCP server stdin is closed")
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        server.process.stdin.write(json.dumps(notification, ensure_ascii=False) + "\n")
        server.process.stdin.flush()

    def _append_call_record(self, agent_id: str, capability: dict, runtime_id: str,
                            tool_name: str, args: dict, run_id: Optional[str],
                            session_id: str, started_at: str, status: str,
                            result=None, error: Optional[str] = None):
        if not run_id:
            return
        record = {
            "session_id": session_id or "",
            "run_id": run_id,
            "agent_id": agent_id,
            "capability_id": capability.get("capability_id") or runtime_id,
            "capability_version_id": capability.get("capability_version_id"),
            "call_type": "mcp",
            "tool_name": tool_name,
            "permissions_used": ["run_command"],
            "input_summary": summarize_mcp_input(tool_name, args or {}),
            "output_summary": summarize_mcp_output(result) if result is not None else {},
            "status": status,
            "error": error,
            "started_at": started_at,
            "completed_at": now_iso(),
        }
        append_tool_call_record(record, workspace_root=self.workspace_root)

    def _is_running(self, runtime_id: str) -> bool:
        server = self._servers.get(runtime_id)
        return bool(server and server.process.poll() is None)

    def _cleanup_exited(self):
        for runtime_id, server in list(self._servers.items()):
            if server.process.poll() is not None:
                self._servers.pop(runtime_id, None)
