"""
host.client — HTTP client that talks to the container's OrchestratorServer.

Used by DockerContainerManager to communicate with running containers.
"""

import json
import urllib.request
import urllib.error
from typing import Optional


class OrchestratorClient:
    """HTTP client for the container-side OrchestratorServer."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}"

    def _request(self, method: str, path: str, body: Optional[dict] = None,
                 timeout: int = 300) -> dict:
        """Make an HTTP request to the orchestrator."""
        url = f"{self.base_url}{path}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None

        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json; charset=utf-8"} if data else {},
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"status": "error", "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"status": "error", "error": f"Connection failed: {e.reason}"}

    # ---- Health ----

    def health_check(self) -> dict:
        return self._request("GET", "/api/health")

    # ---- Agents ----

    def create_agent(self, agent_id: str, role: str = "助手",
                     system_prompt: str = "", workspace_name: str = "") -> dict:
        return self._request("POST", "/api/agents/create", {
            "agent_id": agent_id,
            "role": role,
            "system_prompt": system_prompt,
            "workspace_name": workspace_name or role or agent_id,
        })

    def remove_agent(self, agent_id: str) -> dict:
        return self._request("DELETE", f"/api/agents/{agent_id}")

    def list_agents(self) -> dict:
        return self._request("GET", "/api/agents")

    # ---- Messaging ----

    def send_to_agent(self, agent_id: str, message: str) -> dict:
        return self._request("POST", f"/api/agents/{agent_id}/send", {
            "message": message,
        })

    def send_chain(self, messages: list[dict]) -> dict:
        return self._request("POST", "/api/agents/chain", {
            "messages": messages,
        })

    def delegate(self, message: str, moderator_id: str = "moderator",
                 target_agent_ids: Optional[list[str]] = None) -> dict:
        body = {
            "message": message,
            "moderator_id": moderator_id,
        }
        if target_agent_ids is not None:
            body["target_agent_ids"] = target_agent_ids
        return self._request("POST", "/api/agents/delegate", body)

    # ---- History ----

    def get_agent_history(self, agent_id: str, limit: int = 0) -> dict:
        query = f"?limit={limit}" if limit else ""
        return self._request("GET", f"/api/agents/{agent_id}/history{query}")

    # ---- File operations ----

    def read_file(self, agent_id: str, path: str) -> dict:
        """Read a file from the container's workspace."""
        import urllib.parse
        return self._request("GET",
            f"/api/agents/{agent_id}/read_file?path={urllib.parse.quote(path)}")

    def read_raw_file(self, agent_id: str, path: str) -> tuple[bytes, str]:
        """Read raw file content with MIME type for browser rendering.

        Returns:
            (content_bytes, mime_type)
        """
        import urllib.parse
        url = f"{self.base_url}/api/agents/{agent_id}/raw_file?path={urllib.parse.quote(path)}"
        return self._raw_request(url)

    def upload_agent_file(self, agent_id: str, path: str, filename: str,
                          content: bytes, content_type: str = "application/octet-stream") -> dict:
        import uuid
        boundary = f"----WeAgent{uuid.uuid4().hex}"
        safe_filename = filename.replace('"', '')
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="path"\r\n\r\n',
            path.encode("utf-8"),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{safe_filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self.base_url}/api/agents/{agent_id}/upload_file",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"status": "error", "error": raw}

    def delete_agent_file(self, agent_id: str, path: str) -> dict:
        return self._request("POST", f"/api/agents/{agent_id}/delete_file", {
            "path": path,
        })

    def list_file_tree(self, root: str = "/workspace", include_hidden: bool = False,
                       max_depth: int = 8) -> dict:
        """Return workspace file tree."""
        import urllib.parse
        query = (
            f"root={urllib.parse.quote(root)}"
            f"&include_hidden={str(include_hidden).lower()}"
            f"&max_depth={max_depth}"
        )
        return self._request("GET", f"/api/files/tree?{query}")

    def read_session_raw_file(self, path: str) -> tuple[bytes, str]:
        """Read raw file content without requiring an agent id."""
        import urllib.parse
        url = f"{self.base_url}/api/files/raw?path={urllib.parse.quote(path)}"
        return self._raw_request(url)

    def download_file(self, path: str) -> tuple[bytes, str, str]:
        """Read file bytes for host-side download response."""
        import urllib.parse
        url = f"{self.base_url}/api/files/download?path={urllib.parse.quote(path)}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "application/octet-stream")
                disposition = resp.headers.get("Content-Disposition", "")
                return resp.read(), content_type, disposition
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError(path)
            raise

    def _raw_request(self, url: str) -> tuple[bytes, str]:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "text/plain")
                return resp.read(), content_type
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError(url)
            raise

    # ---- Agent control ----

    def stop_agent(self, agent_id: str) -> dict:
        """Stop an agent's current execution."""
        return self._request("POST", f"/api/agents/{agent_id}/stop")

    # ---- Progress ----

    def get_agent_progress(self, agent_id: str) -> dict:
        return self._request("GET", f"/api/agents/{agent_id}/progress")

    def get_agent_events(self, agent_id: str, since: int = 0) -> dict:
        return self._request("GET", f"/api/agents/{agent_id}/events?since={since}")

    # ---- Session ----

    def get_session_info(self) -> dict:
        return self._request("GET", "/api/session")

    # ---- Tools ----

    def list_tools(self) -> dict:
        return self._request("GET", "/api/tools")

    def execute_tool(self, agent_id: str, tool_name: str, args: dict) -> dict:
        return self._request("POST", "/api/tools/execute", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "args": args,
        })

    def install_tool(self, spec: dict) -> dict:
        return self._request("POST", "/api/tools/install", spec)

    def list_custom_tools(self) -> dict:
        return self._request("GET", "/api/tools/custom")

    def remove_custom_tool(self, tool_name: str) -> dict:
        return self._request("DELETE", f"/api/tools/custom/{tool_name}")

    # ---- Services ----

    def list_services(self) -> dict:
        return self._request("GET", "/api/services")

    def start_service(self, data: dict) -> dict:
        return self._request("POST", "/api/services/start", data)

    def stop_service(self, port: int) -> dict:
        return self._request("POST", f"/api/services/{port}/stop")

    def service_logs(self, port: int) -> dict:
        return self._request("GET", f"/api/services/{port}/logs")
