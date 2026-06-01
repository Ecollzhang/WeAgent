import os
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from app.sandbox.container.service_manager import ServiceManager


class SandboxServiceManagerStage1Test(unittest.TestCase):
    def test_start_list_logs_and_stop_service(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "workspace")
            service_root = os.path.join(workspace, ".session", "services")
            app_dir = os.path.join(workspace, "agents", "frontend")
            os.makedirs(app_dir, exist_ok=True)
            with open(os.path.join(app_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write("hello service")

            port = self._free_port()
            manager = ServiceManager(
                service_root=service_root,
                workspace_root=workspace,
                health_timeout=5,
            )
            result = manager.start_service(
                agent_id="frontend",
                name="frontend preview",
                cwd=app_dir,
                command=f'"{sys.executable}" -m http.server {port} --bind 127.0.0.1',
                port=port,
                service_type="static",
            )

            self.assertEqual("ok", result["status"])
            service_id = result["service"]["id"]
            service = self._wait_for_status(manager, service_id, "running")
            self.assertEqual(port, service["port"])
            self.assertEqual("frontend", service["agent_id"])

            listed = manager.list_services()
            self.assertEqual([service_id], [item["id"] for item in listed])

            logs = manager.get_logs(service_id)
            self.assertEqual(service_id, logs["service_id"])
            self.assertIn(logs["status"], {"starting", "running"})

            stopped = manager.stop_service(service_id)
            self.assertEqual("ok", stopped["status"])
            self.assertEqual("stopped", stopped["service"]["status"])

    def test_rejects_cwd_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "workspace")
            service_root = os.path.join(workspace, ".session", "services")
            outside = os.path.join(tmpdir, "outside")
            os.makedirs(workspace, exist_ok=True)
            os.makedirs(outside, exist_ok=True)
            manager = ServiceManager(service_root=service_root, workspace_root=workspace)

            with self.assertRaises(ValueError):
                manager.start_service(
                    agent_id="agent",
                    name="bad",
                    cwd=outside,
                    command="python -m http.server",
                    port=self._free_port(),
                )

    def test_rejects_command_port_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "workspace")
            service_root = os.path.join(workspace, ".session", "services")
            app_dir = os.path.join(workspace, "agents", "frontend")
            os.makedirs(app_dir, exist_ok=True)
            manager = ServiceManager(service_root=service_root, workspace_root=workspace)

            with self.assertRaisesRegex(ValueError, "does not match command port"):
                manager.start_service(
                    agent_id="frontend",
                    name="frontend preview",
                    cwd=app_dir,
                    command="npm run serve -- --host 0.0.0.0 --port 8080",
                    port=8081,
                    service_type="vite",
                )

    def test_rejects_occupied_requested_port_instead_of_shifting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "workspace")
            service_root = os.path.join(workspace, ".session", "services")
            app_dir = os.path.join(workspace, "agents", "frontend")
            os.makedirs(app_dir, exist_ok=True)
            manager = ServiceManager(service_root=service_root, workspace_root=workspace)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                sock.listen(1)
                port = int(sock.getsockname()[1])

                with self.assertRaisesRegex(ValueError, f"port {port} is already in use"):
                    manager.start_service(
                        agent_id="frontend",
                        name="frontend preview",
                        cwd=app_dir,
                        command=f"{sys.executable} -m http.server {port}",
                        port=port,
                        service_type="static",
                    )

    def test_vite_service_command_gets_proxy_base(self):
        with patch.dict(os.environ, {"SESSION_ID": "session-1"}):
            manager = ServiceManager(service_root=tempfile.mkdtemp(), workspace_root=tempfile.mkdtemp())
            command, base = manager._prepare_command(
                "npx vite --host 0.0.0.0 --port 5173",
                "vite",
                "svc_123",
            )

        self.assertEqual("/api/sandbox/sessions/session-1/services/svc_123/proxy/", base)
        self.assertIn("--base /api/sandbox/sessions/session-1/services/svc_123/proxy/", command)

    def test_vite_service_keeps_existing_base(self):
        with patch.dict(os.environ, {"SESSION_ID": "session-1"}):
            manager = ServiceManager(service_root=tempfile.mkdtemp(), workspace_root=tempfile.mkdtemp())
            command, _ = manager._prepare_command(
                "npx vite --host 0.0.0.0 --port 5173 --base /custom/",
                "vite",
                "svc_123",
            )

        self.assertEqual(
            "npx vite --host 0.0.0.0 --port 5173 --base /custom/",
            command,
        )

    def test_restart_reuses_existing_service_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "workspace")
            service_root = os.path.join(workspace, ".session", "services")
            app_dir = os.path.join(workspace, "agents", "frontend")
            os.makedirs(app_dir, exist_ok=True)

            port = self._free_port()
            manager = ServiceManager(
                service_root=service_root,
                workspace_root=workspace,
                health_timeout=5,
            )
            result = manager.start_service(
                agent_id="frontend",
                name="frontend preview",
                cwd=app_dir,
                command=f'"{sys.executable}" -m http.server {port} --bind 127.0.0.1',
                port=port,
                service_type="static",
            )
            service_id = result["service"]["id"]
            self._wait_for_status(manager, service_id, "running")

            restarted = manager.restart_service(service_id)

            self.assertEqual("ok", restarted["status"])
            self.assertEqual(service_id, restarted["service"]["id"])
            self.assertEqual([service_id], [item["id"] for item in manager.list_services()])
            manager.stop_service(service_id)

    def test_list_services_dedupes_old_restart_duplicates(self):
        services = ServiceManager._dedupe_services([
            {
                "id": "svc_old",
                "name": "preview",
                "cwd": "/workspace/agents/frontend",
                "port": 5173,
                "type": "vite",
                "status": "stopped",
                "updated_at": "2026-06-01T01:00:00",
            },
            {
                "id": "svc_new",
                "name": "preview",
                "cwd": "/workspace/agents/frontend",
                "port": 5173,
                "type": "vite",
                "status": "running",
                "updated_at": "2026-06-01T02:00:00",
            },
        ])

        self.assertEqual(["svc_new"], [service["id"] for service in services])

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _wait_for_status(manager: ServiceManager, service_id: str, status: str) -> dict:
        deadline = time.time() + 5
        last = {}
        while time.time() < deadline:
            last = manager.get_service(service_id) or {}
            if last.get("status") == status:
                return last
            time.sleep(0.1)
        raise AssertionError(f"service {service_id} did not reach {status}, last={last}")


if __name__ == "__main__":
    unittest.main()
