from __future__ import annotations

import json
import os
import re
import signal
import shlex
import socket
import subprocess
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from .logging_utils import log_event


class ServiceManager:
    """Manage preview service processes inside one sandbox container."""

    def __init__(
        self,
        service_root: str = "/workspace/.session/services",
        workspace_root: str = "/workspace",
        health_timeout: float = 15.0,
    ):
        self.service_root = service_root
        self.workspace_root = os.path.abspath(workspace_root)
        self.health_timeout = health_timeout
        self._lock = threading.Lock()
        self._processes: dict[str, subprocess.Popen] = {}
        self._services: dict[str, dict[str, Any]] = {}
        os.makedirs(self.service_root, exist_ok=True)
        self._load_services()

    def start_service(
        self,
        agent_id: str,
        name: str,
        cwd: str,
        command: str,
        port: int,
        service_type: str = "custom",
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        cwd = self._validate_cwd(cwd)
        requested_port = int(port or 0)
        command_port = self._declared_command_port(command)
        if requested_port > 0 and command_port and command_port != requested_port:
            raise ValueError(
                f"declared service port {requested_port} does not match command port {command_port}"
            )
        port = self._pick_port(requested_port)
        service_id = f"svc_{uuid.uuid4().hex[:12]}"
        command, proxy_base_path = self._prepare_command(command, service_type, service_id)
        service_dir = self._service_dir(service_id)
        os.makedirs(service_dir, exist_ok=True)
        stdout_path = os.path.join(service_dir, "stdout.log")
        stderr_path = os.path.join(service_dir, "stderr.log")

        meta = {
            "id": service_id,
            "agent_id": agent_id or "",
            "name": name or service_id,
            "type": service_type or "custom",
            "cwd": cwd,
            "command": command,
            "proxy_base_path": proxy_base_path,
            "port": port,
            "status": "starting",
            "pid": None,
            "created_at": self._now(),
            "updated_at": self._now(),
            "last_error": "",
            "stdout_log": stdout_path,
            "stderr_log": stderr_path,
        }
        self._write_meta(meta)

        stdout_file = open(stdout_path, "ab", buffering=0)
        stderr_file = open(stderr_path, "ab", buffering=0)
        child_env = os.environ.copy()
        child_env.update({str(k): str(v) for k, v in (env or {}).items()})
        child_env.setdefault("HOST", "0.0.0.0")
        child_env.setdefault("PORT", str(port))

        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=stdout_file,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                env=child_env,
                preexec_fn=os.setsid if os.name != "nt" and hasattr(os, "setsid") else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except Exception as exc:
            stdout_file.close()
            stderr_file.close()
            meta["status"] = "failed"
            meta["last_error"] = str(exc)
            meta["updated_at"] = self._now()
            self._write_meta(meta)
            log_event("service_start_failed", service_id=service_id, error=str(exc))
            return {"status": "error", "service": meta, "error": str(exc)}

        stdout_file.close()
        stderr_file.close()
        meta["pid"] = proc.pid
        with self._lock:
            self._processes[service_id] = proc
            self._services[service_id] = meta
        self._write_meta(meta)
        log_event("service_process_started", service_id=service_id, pid=proc.pid, port=port, cwd=cwd)

        threading.Thread(target=self._watch_process, args=(service_id,), daemon=True).start()
        threading.Thread(target=self._await_health, args=(service_id,), daemon=True).start()
        return {"status": "ok", "service": self.get_service(service_id)}

    def stop_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        if not service:
            return {"error": "service not found"}
        proc = self._processes.get(service_id)
        service["status"] = "stopping"
        service["updated_at"] = self._now()
        self._write_meta(service)
        if proc and proc.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                elif hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    pass
            except Exception as exc:
                service["last_error"] = str(exc)
        service["status"] = "stopped"
        service["updated_at"] = self._now()
        self._write_meta(service)
        log_event("service_stopped", service_id=service_id)
        return {"status": "ok", "service": service}

    def restart_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        if not service:
            return {"error": "service not found"}
        self.stop_service(service_id)
        return self._start_existing_service(service)

    def _start_existing_service(self, service: dict[str, Any]) -> dict[str, Any]:
        service_id = service.get("id", "")
        if not service_id:
            return {"error": "service id required"}
        cwd = self._validate_cwd(service.get("cwd", self.workspace_root))
        port = int(service.get("port") or 0)
        if port <= 0:
            return {"error": "service port required"}
        if self._port_open(port):
            return {"status": "error", "service": service, "error": f"port {port} is already in use"}

        service_dir = self._service_dir(service_id)
        os.makedirs(service_dir, exist_ok=True)
        stdout_path = service.get("stdout_log") or os.path.join(service_dir, "stdout.log")
        stderr_path = service.get("stderr_log") or os.path.join(service_dir, "stderr.log")
        service.update({
            "cwd": cwd,
            "status": "starting",
            "pid": None,
            "updated_at": self._now(),
            "restarted_at": self._now(),
            "last_error": "",
            "stdout_log": stdout_path,
            "stderr_log": stderr_path,
        })
        self._write_meta(service)

        stdout_file = open(stdout_path, "ab", buffering=0)
        stderr_file = open(stderr_path, "ab", buffering=0)
        child_env = os.environ.copy()
        child_env.setdefault("HOST", "0.0.0.0")
        child_env.setdefault("PORT", str(port))

        try:
            proc = subprocess.Popen(
                service.get("command", ""),
                cwd=cwd,
                shell=True,
                stdout=stdout_file,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                env=child_env,
                preexec_fn=os.setsid if os.name != "nt" and hasattr(os, "setsid") else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except Exception as exc:
            stdout_file.close()
            stderr_file.close()
            service["status"] = "failed"
            service["last_error"] = str(exc)
            service["updated_at"] = self._now()
            self._write_meta(service)
            log_event("service_restart_failed", service_id=service_id, error=str(exc))
            return {"status": "error", "service": service, "error": str(exc)}

        stdout_file.close()
        stderr_file.close()
        service["pid"] = proc.pid
        service["updated_at"] = self._now()
        with self._lock:
            self._processes[service_id] = proc
            self._services[service_id] = dict(service)
        self._write_meta(service)
        log_event("service_restarted", service_id=service_id, pid=proc.pid, port=port, cwd=cwd)

        threading.Thread(target=self._watch_process, args=(service_id,), daemon=True).start()
        threading.Thread(target=self._await_health, args=(service_id,), daemon=True).start()
        return {"status": "ok", "service": self.get_service(service_id)}

    def list_services(self) -> list[dict[str, Any]]:
        with self._lock:
            service_ids = list(self._services.keys())
        services = [svc for service_id in service_ids if (svc := self.get_service(service_id))]
        return self._dedupe_services(services)

    def get_service(self, service_id: str) -> dict[str, Any] | None:
        with self._lock:
            service = self._services.get(service_id)
            proc = self._processes.get(service_id)
        if not service:
            service = self._read_meta(service_id)
            if not service:
                return None
        service = dict(service)
        if proc and proc.poll() is not None and service.get("status") not in {"stopped", "failed"}:
            service["status"] = "exited"
            service["updated_at"] = self._now()
            self._write_meta(service)
        return service

    def get_logs(self, service_id: str, tail_bytes: int = 65536) -> dict[str, Any]:
        service = self.get_service(service_id)
        if not service:
            return {"error": "service not found"}
        return {
            "service_id": service_id,
            "status": service.get("status"),
            "stdout_tail": self._tail(service.get("stdout_log", ""), tail_bytes),
            "stderr_tail": self._tail(service.get("stderr_log", ""), tail_bytes),
        }

    def stop_all(self) -> None:
        for service in self.list_services():
            self.stop_service(service["id"])

    def _await_health(self, service_id: str) -> None:
        deadline = time.time() + self.health_timeout
        while time.time() < deadline:
            service = self.get_service(service_id)
            if not service or service.get("status") in {"failed", "stopped", "exited"}:
                return
            if self._port_open(int(service.get("port") or 0)):
                service["status"] = "running"
                service["updated_at"] = self._now()
                self._write_meta(service)
                log_event("service_running", service_id=service_id, port=service.get("port"))
                return
            time.sleep(0.3)
        service = self.get_service(service_id)
        if service and service.get("status") == "starting":
            service["status"] = "failed"
            service["last_error"] = f"port {service.get('port')} did not become ready"
            service["updated_at"] = self._now()
            self._write_meta(service)
            log_event("service_health_failed", service_id=service_id, port=service.get("port"))

    def _watch_process(self, service_id: str) -> None:
        proc = self._processes.get(service_id)
        if not proc:
            return
        returncode = proc.wait()
        service = self.get_service(service_id)
        if service and service.get("status") not in {"stopped", "stopping", "failed"}:
            service["status"] = "exited"
            service["returncode"] = returncode
            service["updated_at"] = self._now()
            self._write_meta(service)
            log_event("service_exited", service_id=service_id, returncode=returncode)

    def _validate_cwd(self, cwd: str) -> str:
        if not cwd:
            raise ValueError("cwd is required")
        path = os.path.abspath(cwd)
        root = self.workspace_root
        if path != root and not path.startswith(root + os.sep):
            raise ValueError("cwd must be under /workspace")
        if not os.path.isdir(path):
            raise ValueError(f"cwd does not exist: {cwd}")
        return path

    def _pick_port(self, requested: int) -> int:
        if requested > 0:
            if self._port_open(requested):
                raise ValueError(f"port {requested} is already in use")
            return requested
        base = requested if requested > 0 else 5173
        for port in range(base, base + 100):
            if not self._port_open(port):
                return port
        raise ValueError("no available service port")

    @staticmethod
    def _declared_command_port(command: str) -> int | None:
        text = command or ""
        patterns = (
            r"(?:^|\s)--port(?:=|\s+)(\d{2,5})(?=\s|$)",
            r"(?:^|\s)-p\s+(\d{2,5})(?=\s|$)",
            r"\bhttp\.server\s+(\d{2,5})(?=\s|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    def _prepare_command(self, command: str, service_type: str, service_id: str) -> tuple[str, str]:
        proxy_base_path = self._proxy_base_path(service_id)
        if self._is_vite_service(command, service_type) and not self._has_cli_option(command, "--base"):
            return f"{command} --base {shlex.quote(proxy_base_path)}", proxy_base_path
        return command, proxy_base_path

    @staticmethod
    def _is_vite_service(command: str, service_type: str) -> bool:
        text = f"{service_type or ''} {command or ''}".lower()
        return "vite" in text

    @staticmethod
    def _has_cli_option(command: str, option: str) -> bool:
        return bool(re.search(rf"(^|\s){re.escape(option)}(?:=|\s|$)", command or ""))

    @staticmethod
    def _proxy_base_path(service_id: str) -> str:
        session_id = os.environ.get("SESSION_ID", "").strip()
        if not session_id:
            return "/"
        return f"/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/"

    @staticmethod
    def _port_open(port: int) -> bool:
        if port <= 0:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def _load_services(self) -> None:
        if not os.path.isdir(self.service_root):
            return
        for name in os.listdir(self.service_root):
            meta = self._read_meta(name)
            if meta:
                self._services[meta["id"]] = meta

    @staticmethod
    def _dedupe_services(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
        order: list[tuple[Any, ...]] = []
        for service in services:
            key = (
                service.get("name") or "",
                service.get("cwd") or "",
                service.get("port") or 0,
                service.get("type") or "",
            )
            current = by_key.get(key)
            if current is None:
                by_key[key] = service
                order.append(key)
                continue
            current_time = str(current.get("updated_at") or current.get("created_at") or "")
            service_time = str(service.get("updated_at") or service.get("created_at") or "")
            if service_time >= current_time:
                by_key[key] = service
        return [by_key[key] for key in order if key in by_key]

    def _service_dir(self, service_id: str) -> str:
        return os.path.join(self.service_root, service_id)

    def _meta_path(self, service_id: str) -> str:
        return os.path.join(self._service_dir(service_id), "meta.json")

    def _write_meta(self, service: dict[str, Any]) -> None:
        os.makedirs(self._service_dir(service["id"]), exist_ok=True)
        service["updated_at"] = service.get("updated_at") or self._now()
        with open(self._meta_path(service["id"]), "w", encoding="utf-8") as f:
            json.dump(service, f, ensure_ascii=False, indent=2)
        with self._lock:
            self._services[service["id"]] = dict(service)

    def _read_meta(self, service_id: str) -> dict[str, Any] | None:
        path = self._meta_path(service_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _tail(path: str, tail_bytes: int) -> str:
        if not path or not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - int(tail_bytes or 65536)))
            return f.read().decode("utf-8", errors="replace")

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()
