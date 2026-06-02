"""
host.client — HTTP client that talks to the container's OrchestratorServer.

Used by DockerContainerManager to communicate with running containers.
"""

import json
import os
import threading
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional

import simple_websocket


_BLOCKED_PROXY_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "accept-encoding",
    "sec-websocket-key",
    "sec-websocket-version",
    "sec-websocket-extensions",
    "sec-websocket-protocol",
}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _timeout_from_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


class OrchestratorClient:
    """HTTP client for the container-side OrchestratorServer."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}"

    def _request(self, method: str, path: str, body: Optional[dict] = None,
                 timeout: Optional[int] = None) -> dict:
        """Make an HTTP request to the orchestrator."""
        if timeout is None:
            timeout = int(os.environ.get("SANDBOX_ORCHESTRATOR_TIMEOUT_SECONDS", "7500"))
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
        except TimeoutError:
            return {"status": "error", "error": f"Request timed out after {timeout}s"}

    # ---- Health ----

    def health_check(self) -> dict:
        return self._request(
            "GET",
            "/api/health",
            timeout=_timeout_from_env("SANDBOX_HEALTH_TIMEOUT_SECONDS", 2),
        )

    # ---- Capabilities ----

    def apply_capability_projection(self, projection: dict) -> dict:
        return self._request("POST", "/api/capabilities/projection", projection)

    def collect_skill_drafts(self, agent_id: str = "") -> dict:
        return self._request("POST", "/api/capabilities/drafts/collect", {
            "agent_id": agent_id,
        })

    def get_providers(self) -> dict:
        return self._request("GET", "/api/providers")

    # ---- Agents ----

    def create_agent(self, agent_id: str, role: str = "助手",
                     system_prompt: str = "", workspace_name: str = "",
                     adapter_name: str = "claude") -> dict:
        return self._request("POST", "/api/agents/create", {
            "agent_id": agent_id,
            "role": role,
            "system_prompt": system_prompt,
            "workspace_name": workspace_name or role or agent_id,
            "adapter_name": adapter_name or "claude",
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
        return self._request(
            "GET",
            f"/api/agents/{agent_id}/read_file?path={urllib.parse.quote(path)}",
            timeout=_timeout_from_env("SANDBOX_FILE_TIMEOUT_SECONDS", 5),
        )

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
        return self._request(
            "GET",
            f"/api/files/tree?{query}",
            timeout=_timeout_from_env("SANDBOX_FILE_TIMEOUT_SECONDS", 5),
        )

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

    def restart_agent(self, agent_id: str) -> dict:
        """Restart an agent runtime inside the container."""
        return self._request("POST", f"/api/agents/{agent_id}/restart")

    def update_model_config(self, config: dict) -> dict:
        """Hot-update model config inside the container."""
        return self._request(
            "POST",
            "/api/config/model",
            config,
            timeout=_timeout_from_env("SANDBOX_CONFIG_UPDATE_TIMEOUT_SECONDS", 5),
        )

    # ---- Progress ----

    def get_agent_progress(self, agent_id: str) -> dict:
        return self._request("GET", f"/api/agents/{agent_id}/progress")

    def get_agent_events(self, agent_id: str, since: int = 0) -> dict:
        return self._request("GET", f"/api/agents/{agent_id}/events?since={since}")

    # ---- Session ----

    def get_session_info(self) -> dict:
        return self._request(
            "GET",
            "/api/session",
            timeout=_timeout_from_env("SANDBOX_SESSION_INFO_TIMEOUT_SECONDS", 3),
        )

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

    # ---- MCP ----

    def list_mcp_servers(self) -> dict:
        return self._request("GET", "/api/mcp/servers")

    def start_mcp_server(self, agent_id: str, runtime_id: str) -> dict:
        return self._request("POST", f"/api/mcp/{runtime_id}/start", {
            "agent_id": agent_id,
        })

    def list_mcp_tools(self, runtime_id: str) -> dict:
        return self._request("GET", f"/api/mcp/{runtime_id}/tools")

    def call_mcp_tool(self, agent_id: str, runtime_id: str, tool_name: str,
                      args: dict) -> dict:
        return self._request("POST", f"/api/mcp/{runtime_id}/call", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "args": args,
        })

    def stop_mcp_server(self, runtime_id: str) -> dict:
        return self._request("POST", f"/api/mcp/{runtime_id}/stop")

    # ---- Services ----

    def list_services(self) -> dict:
        return self._request("GET", "/api/services")

    def get_service(self, service_id: str) -> dict:
        return self._request("GET", f"/api/services/{service_id}")

    def start_service(self, data: dict) -> dict:
        return self._request("POST", "/api/services/start", data)

    def stop_service(self, service_id: str) -> dict:
        return self._request("POST", f"/api/services/{service_id}/stop")

    def restart_service(self, service_id: str) -> dict:
        return self._request("POST", f"/api/services/{service_id}/restart")

    def service_logs(self, service_id: str, tail_bytes: int = 65536) -> dict:
        return self._request("GET", f"/api/services/{service_id}/logs?tail_bytes={tail_bytes}")

    def proxy_service(
        self,
        service_id: str,
        path: str,
        method: str,
        headers: dict | None = None,
        body: bytes | None = None,
        query_string: str = "",
        timeout: Optional[int] = None,
    ) -> dict:
        if timeout is None:
            timeout = int(os.environ.get("SANDBOX_SERVICE_PROXY_TIMEOUT_SECONDS", "60"))
        quoted_service_id = urllib.parse.quote(service_id, safe="")
        quoted_path = urllib.parse.quote(path or "", safe="/:@!$&'()*+,;=-._~")
        url = f"{self.base_url}/api/services/{quoted_service_id}/proxy/{quoted_path}"
        if query_string:
            url = f"{url}?{query_string}"

        request_headers = {
            str(key): str(value)
            for key, value in (headers or {}).items()
            if str(key).lower() not in _BLOCKED_PROXY_HEADERS
        }
        data = body if body else None
        req = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
        opener = urllib.request.build_opener(_NoRedirectHandler)

        try:
            with opener.open(req, timeout=timeout) as resp:
                return {
                    "status_code": resp.status,
                    "headers": list(resp.headers.items()),
                    "body": resp.read(),
                }
        except urllib.error.HTTPError as exc:
            return {
                "status_code": exc.code,
                "headers": list(exc.headers.items()),
                "body": exc.read(),
            }
        except urllib.error.URLError as exc:
            return {
                "status_code": 502,
                "headers": [("Content-Type", "text/plain; charset=utf-8")],
                "body": f"Sandbox service proxy failed: {exc.reason}".encode("utf-8"),
            }

    def proxy_service_websocket(
        self,
        service_id: str,
        path: str,
        client_ws,
        headers: dict | None = None,
        query_string: str = "",
    ) -> dict:
        quoted_service_id = urllib.parse.quote(service_id, safe="")
        quoted_path = urllib.parse.quote(path or "", safe="/:@!$&'()*+,;=-._~")
        url = self._websocket_url(f"/api/services/{quoted_service_id}/proxy/{quoted_path}")
        if query_string:
            url = f"{url}?{query_string}"

        request_headers = {
            str(key): str(value)
            for key, value in (headers or {}).items()
            if str(key).lower() not in _BLOCKED_PROXY_HEADERS
        }
        upstream_ws = simple_websocket.Client.connect(url, headers=request_headers)
        return _relay_websockets(client_ws, upstream_ws)

    def _websocket_url(self, path: str) -> str:
        parsed = urllib.parse.urlsplit(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urllib.parse.urlunsplit((scheme, parsed.netloc, path, "", ""))


def _relay_websockets(left, right) -> dict:
    stop = threading.Event()

    def close_both():
        for ws in (left, right):
            try:
                ws.close()
            except Exception:
                pass

    def pump(source, target):
        while not stop.is_set():
            try:
                message = source.receive()
            except simple_websocket.ConnectionClosed:
                break
            except Exception:
                break
            if message is None:
                break
            try:
                target.send(message)
            except Exception:
                break
        stop.set()
        close_both()

    threads = [
        threading.Thread(target=pump, args=(left, right), daemon=True),
        threading.Thread(target=pump, args=(right, left), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"status": "closed"}
