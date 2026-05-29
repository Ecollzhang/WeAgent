"""
host.manager — DockerContainerManager

Manages the full lifecycle of sandbox containers on the host side.

Each session (conversation) gets its own Docker container.
The container runs an OrchestratorServer on port 8080 (mapped to a random host port).
Communication: host → HTTP → container's Orchestrator.
All files stay inside the container — no host volume mounts.
"""

import io
import json
import os
import posixpath
import socket
import tarfile
import threading
import time
from typing import Optional
from urllib.parse import urlparse

from .client import OrchestratorClient


# Lock for thread safety
_lock = threading.Lock()


def _clean_config_value(value: str = "") -> str:
    text = str(value or "").strip()
    text = text.strip(" \t\r\n'\"")
    return text


def _clean_base_url(value: str = "") -> str:
    text = _clean_config_value(value).rstrip("/")
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {text}")
    return text


class DockerNotAvailableError(RuntimeError):
    """Raised when Docker SDK is not installed or Docker is not running."""
    pass


class SessionContainer:
    """Represents a running session container."""
    def __init__(self, session_id: str, container_id: str, host_port: int,
                 agents_config: list[dict], service_ports: Optional[dict[str, int]] = None):
        self.session_id = session_id
        self.container_id = container_id
        self.host_port = host_port
        self.agents_config = agents_config
        self.service_ports = service_ports or {}
        self.created_at = time.time()
        self.client = OrchestratorClient(host="localhost", port=host_port)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "container_id": self.container_id[:12] + "...",
            "host_port": self.host_port,
            "orchestrator_host_port": self.host_port,
            "service_ports": self.service_ports,
            "service_urls": {
                port: f"http://localhost:{mapped_port}"
                for port, mapped_port in self.service_ports.items()
            },
            "agents": self.agents_config,
            "workspace": {
                "root": "/workspace",
                "shared_dir": "/workspace/shared",
                "agents_dir": "/workspace/agents",
            },
            "alive": self._check_alive(),
            "created_at": self.created_at,
        }

    def _check_alive(self) -> bool:
        try:
            resp = self.client.health_check()
            return resp.get("status") == "ok"
        except Exception:
            return False


class DockerContainerManager:
    """
    Manages Docker containers for sandbox sessions.

    Uses docker Python SDK. Each session = one container.
    """

    def __init__(self, image_name: str = "weagent-sandbox:latest"):
        self.image_name = image_name
        self._sessions: dict[str, SessionContainer] = {}
        self._docker = None  # lazy import

    # ---- Docker client ----

    @property
    def docker(self):
        if self._docker is None:
            try:
                import docker
            except ImportError:
                raise DockerNotAvailableError(
                    "Docker Python SDK not installed. Run: pip install docker"
                )
            self._docker = docker.from_env()
        return self._docker

    # ---- Image management ----

    def build_image(self, dockerfile_dir: str = None) -> str:
        """Build the sandbox Docker image."""
        if dockerfile_dir is None:
            dockerfile_dir = os.path.join(os.path.dirname(__file__), "..")

        print(f"[DockerManager] Building image {self.image_name} from {dockerfile_dir}...")
        image, _ = self.docker.images.build(
            path=dockerfile_dir,
            tag=self.image_name,
            dockerfile="Dockerfile",
        )
        print(f"[DockerManager] Image built: {image.id[:12]}")
        return self.image_name

    def ensure_image(self) -> bool:
        """Check if image exists, return True if ready."""
        try:
            self.docker.images.get(self.image_name)
            return True
        except Exception:
            return False

    # ---- Session lifecycle ----

    def create_session(self, session_id: str, agents: list[dict],
                        env_vars: Optional[dict] = None) -> SessionContainer:
        """
        Create a new sandbox session (starts a Docker container).

        Args:
            session_id: Unique session/conversation ID
            agents: List of agent configs:
                [{"agent_id": "pm", "role": "产品经理", "system_prompt": "..."},
                 {"agent_id": "frontend", "role": "前端", "system_prompt": "..."}]
            env_vars: Extra env vars to pass to container (e.g. ANTHROPIC_API_KEY)

        Returns:
            SessionContainer
        """
        if not self.ensure_image():
            raise RuntimeError(
                f"Docker image '{self.image_name}' not found. "
                "Run build_image() first."
            )

        # Build container env: orchestrator defaults + user env vars
        container_env = {
            "ORCHESTRATOR_PORT": "8080",
            "SESSION_ID": session_id,
            "HOST_CALLBACK_URL": env_vars.get("HOST_CALLBACK_URL") if env_vars and env_vars.get("HOST_CALLBACK_URL") else f"http://host.docker.internal:{os.getenv('PORT', '5001')}",
        }
        # Pass through provider env vars if provided. The container runners
        # translate these into each provider's private home/config.
        provider_env_keys = [
            "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
            "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
            "CODEX_API_KEY", "CODEX_BASE_URL", "CODEX_MODEL",
            "CODEX_AUTH_JSON", "CODEX_CONFIG_TOML",
            "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
            "API_TIMEOUT_MS", "CLAUDE_EXEC_TIMEOUT_SECONDS",
            "CODEX_EXEC_TIMEOUT_SECONDS", "OPENCODE_EXEC_TIMEOUT_SECONDS",
            "AGENT_EXEC_TIMEOUT_SECONDS",
            "HTTP_PROXY", "HTTPS_PROXY",
        ]
        if env_vars:
            for key in provider_env_keys:
                if key in env_vars:
                    if key.endswith("BASE_URL"):
                        container_env[key] = _clean_base_url(env_vars[key])
                    elif key in {
                        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                        "ANTHROPIC_MODEL", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL",
                        "OPENAI_API_KEY", "OPENAI_MODEL",
                        "CODEX_API_KEY", "CODEX_MODEL",
                        "OPENCODE_API_KEY", "OPENCODE_MODEL",
                    }:
                        container_env[key] = _clean_config_value(env_vars[key])
                    else:
                        container_env[key] = env_vars[key]

        # Find free ports: one for orchestrator plus common dev-server ports
        host_port = self._find_free_port()
        service_ports = {
            "3000": self._find_free_port(),
            "5173": self._find_free_port(),
            "8000": self._find_free_port(),
            "8081": self._find_free_port(),
            "9000": self._find_free_port(),
        }
        port_bindings = {"8080/tcp": host_port}
        for container_port, mapped_port in service_ports.items():
            port_bindings[f"{container_port}/tcp"] = mapped_port

        # Start container (no host volume mount — files stay inside container only)
        print(
            f"[SandboxManager] create_session session_id={session_id} "
            f"agents={len(agents)} image={self.image_name}"
        )
        container = self.docker.containers.run(
            image=self.image_name,
            detach=True,
            ports=port_bindings,
            environment=container_env,
            mem_limit="1g",
            network_mode="bridge",
            name=f"weagent-{session_id[:12]}",
            labels={
                "weagent.sandbox": "true",
                "weagent.session_id": session_id,
                "weagent.orchestrator_port": "8080",
                "weagent.agents": json.dumps(agents, ensure_ascii=False),
            },
            remove=True,
            extra_hosts={"host.docker.internal": "host-gateway"},
        )

        # Wait for orchestrator to be ready
        self._wait_for_ready(host_port, timeout=30)
        print(
            f"[SandboxManager] container_ready session_id={session_id} "
            f"container={container.id[:12]} orchestrator=http://localhost:{host_port}"
        )

        # Create agents inside container
        for agent_cfg in agents:
            print(
                f"[SandboxManager] create_agent session_id={session_id} "
                f"agent_id={agent_cfg.get('agent_id')} role={agent_cfg.get('role')} "
                f"adapter_name={agent_cfg.get('adapter_name', 'claude')}"
            )
            self._create_agent_in_container(host_port, agent_cfg)

        session = SessionContainer(
            session_id=session_id,
            container_id=container.id,
            host_port=host_port,
            agents_config=agents,
            service_ports=service_ports,
        )

        with _lock:
            self._sessions[session_id] = session

        return session

    def destroy_session(self, session_id: str):
        """Stop and remove a session container."""
        with _lock:
            session = self._sessions.pop(session_id, None)

        if not session:
            self.recover_sessions()
            with _lock:
                session = self._sessions.pop(session_id, None)

        try:
            if session:
                container = self.docker.containers.get(session.container_id)
            else:
                matches = self.docker.containers.list(
                    all=True,
                    filters={
                        "label": [
                            "weagent.sandbox=true",
                            f"weagent.session_id={session_id}",
                        ],
                    },
                )
                container = matches[0] if matches else None
            if not container:
                return
            container.stop(timeout=10)
        except Exception:
            pass

    def get_session(self, session_id: str) -> Optional[SessionContainer]:
        self.recover_sessions()
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[SessionContainer]:
        self.recover_sessions()
        with _lock:
            return list(self._sessions.values())

    def recover_sessions(self):
        """Recover running sandbox containers after host process restart."""
        try:
            containers = self.docker.containers.list(
                filters={"label": "weagent.sandbox=true"}
            )
        except Exception:
            return

        recovered = {}
        for container in containers:
            session_id = container.labels.get("weagent.session_id")
            if not session_id:
                continue
            if session_id in self._sessions:
                continue

            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            binding = ports.get("8080/tcp") or []
            if not binding:
                continue
            try:
                host_port = int(binding[0].get("HostPort"))
            except (TypeError, ValueError):
                continue

            service_ports = {}
            for container_port in ["3000", "5173", "8000", "8081", "9000"]:
                mapped = ports.get(f"{container_port}/tcp") or []
                if mapped:
                    try:
                        service_ports[container_port] = int(mapped[0].get("HostPort"))
                    except (TypeError, ValueError):
                        pass

            agents_config = []
            try:
                info = OrchestratorClient(host="localhost", port=host_port).get_session_info()
                agents_config = info.get("agents", [])
            except Exception:
                pass
            if not agents_config:
                try:
                    agents_config = self._recover_agents_from_labels(container.labels)
                except Exception:
                    agents_config = []

            recovered[session_id] = SessionContainer(
                session_id=session_id,
                container_id=container.id,
                host_port=host_port,
                agents_config=agents_config,
                service_ports=service_ports,
            )

        if recovered:
            with _lock:
                self._sessions.update(recovered)

    # ---- Communication ----

    def send_message(self, session_id: str, agent_id: str, message: str) -> dict:
        """Send a message to an agent in a session."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] send_message session_id={session_id} "
            f"agent_id={agent_id} message_len={len(message or '')}"
        )
        return session.client.send_to_agent(agent_id, message)

    def send_chain(self, session_id: str, messages: list[dict]) -> list[dict]:
        """Chain messages across agents."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] send_chain session_id={session_id} "
            f"message_count={len(messages or [])}"
        )
        return session.client.send_chain(messages)

    def delegate_message(self, session_id: str, message: str,
                         moderator_id: str = "moderator",
                         target_agent_ids: Optional[list[str]] = None) -> dict:
        """Ask the moderator agent to delegate a task within a session."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] delegate_message session_id={session_id} "
            f"moderator_id={moderator_id} targets={target_agent_ids} "
            f"message_len={len(message or '')}"
        )
        return session.client.delegate(message, moderator_id, target_agent_ids)

    def add_agent(self, session_id: str, config: dict) -> dict:
        """Add an agent to an existing session container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] add_agent session_id={session_id} "
            f"agent_id={config.get('agent_id')} role={config.get('role')}"
        )
        result = session.client.create_agent(
            agent_id=config["agent_id"],
            role=config.get("role", "助手"),
            system_prompt=config.get("system_prompt", ""),
            workspace_name=config.get("workspace_name") or config.get("role") or config["agent_id"],
            adapter_name=config.get("adapter_name") or config.get("provider") or "claude",
        )
        if result.get("status") == "ok":
            session.agents_config = [
                a for a in session.agents_config
                if a.get("agent_id") != config["agent_id"]
            ]
            session.agents_config.append(config)
        return result

    def remove_agent(self, session_id: str, agent_id: str) -> dict:
        """Remove an agent from an existing session container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.remove_agent(agent_id)
        if result.get("status") == "ok":
            session.agents_config = [
                a for a in session.agents_config
                if a.get("agent_id") != agent_id
            ]
        return result

    def restart_agent(self, session_id: str, agent_id: str) -> dict:
        """Restart an agent runtime in a session container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.restart_agent(agent_id)

    def update_model_config(self, session_id: str, env_vars: dict) -> dict:
        """Hot-update model configuration in a running session container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        config = {
            "api_key": (
                env_vars.get("ANTHROPIC_API_KEY")
                or env_vars.get("ANTHROPIC_AUTH_TOKEN")
                or env_vars.get("DEEPSEEK_API_KEY")
                or ""
            ),
            "base_url": env_vars.get("ANTHROPIC_BASE_URL") or env_vars.get("DEEPSEEK_BASE_URL") or "",
            "model": env_vars.get("ANTHROPIC_MODEL") or env_vars.get("DEEPSEEK_MODEL") or "",
        }
        config["api_key"] = _clean_config_value(config["api_key"])
        config["base_url"] = _clean_base_url(config["base_url"])
        config["model"] = _clean_config_value(config["model"])
        return session.client.update_model_config(config)

    def update_model_config_for_user_sessions(self, user_id: str, env_vars: dict) -> dict:
        """Hot-update model configuration for all running containers owned by a user."""
        self.recover_sessions()
        from app.models.conversation import Conversation

        conversations = Conversation.query.filter(
            Conversation.owner_id == user_id,
            Conversation.sandbox_session_id.isnot(None),
            Conversation.sandbox_status == "running",
        ).all()
        results = []
        for conversation in conversations:
            session_id = conversation.sandbox_session_id
            try:
                result = self.update_model_config(session_id, env_vars)
                results.append({
                    "conversation_id": conversation.id,
                    "session_id": session_id,
                    "status": result.get("status", "ok"),
                    "error": result.get("error"),
                })
            except Exception as e:
                results.append({
                    "conversation_id": conversation.id,
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e),
                })
        return {"status": "ok", "updated": results}

    def get_agent_history(self, session_id: str, agent_id: str, limit: int = 0) -> list[dict]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.get_agent_history(agent_id, limit)

    def get_session_info(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.get_session_info()

    # ---- File operations ----

    def get_agent_file(self, session_id: str, agent_id: str, path: str) -> dict:
        """Read a file from the container's workspace."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.read_file(agent_id, path)

    def get_agent_raw_file(self, session_id: str, agent_id: str, path: str) -> tuple[bytes, str]:
        """Read raw file content with MIME type from the container.

        Returns:
            (content_bytes, mime_type)
        """
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.read_raw_file(agent_id, path)

    def upload_agent_file(self, session_id: str, agent_id: str, path: str,
                          filename: str, content: bytes,
                          content_type: str = "application/octet-stream") -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        workspace_name = self._workspace_name_for_agent(session, agent_id)
        normalized_path = self._normalize_agent_user_input_path(agent_id, path, workspace_name)
        directory = posixpath.dirname(normalized_path)
        target_name = posixpath.basename(normalized_path)

        try:
            container = self.docker.containers.get(session.container_id)
            mkdir_result = container.exec_run(["mkdir", "-p", directory])
            if getattr(mkdir_result, "exit_code", 1) != 0:
                output = self._decode_exec_output(getattr(mkdir_result, "output", b""))
                return {"status": "error", "error": output or "Failed to create upload directory"}

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                info = tarfile.TarInfo(name=target_name)
                info.size = len(content)
                info.mode = 0o644
                info.mtime = int(time.time())
                tar.addfile(info, io.BytesIO(content))
            tar_stream.seek(0)

            if not container.put_archive(directory, tar_stream.getvalue()):
                return {"status": "error", "error": "Failed to write file into container"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {
            "status": "ok",
            "path": normalized_path,
            "filename": filename,
            "size": len(content),
            "content_type": content_type,
        }

    def delete_agent_file(self, session_id: str, agent_id: str, path: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        workspace_name = self._workspace_name_for_agent(session, agent_id)
        normalized_path = self._normalize_agent_user_input_path(agent_id, path, workspace_name)
        try:
            container = self.docker.containers.get(session.container_id)
            result = container.exec_run(["rm", "-f", normalized_path])
            if getattr(result, "exit_code", 1) != 0:
                output = self._decode_exec_output(getattr(result, "output", b""))
                return {"status": "error", "error": output or "Failed to delete file"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "ok", "path": normalized_path}

    def get_file_tree(self, session_id: str, root: str = "/workspace") -> dict:
        """Return the session workspace file tree."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.list_file_tree(root=root)

    def get_raw_file(self, session_id: str, path: str) -> tuple[bytes, str]:
        """Read a raw workspace file without requiring an agent id."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.read_session_raw_file(path)

    def download_file(self, session_id: str, path: str) -> tuple[bytes, str, str]:
        """Read a workspace file for download."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.download_file(path)

    # ---- Agent control ----

    def stop_agent(self, session_id: str, agent_id: str) -> dict:
        """Stop an agent's current execution."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.stop_agent(agent_id)

    # ---- Progress (via orchestator API inside container) ----

    def get_agent_progress(self, session_id: str, agent_id: str) -> Optional[dict]:
        """Read agent's progress from the container via API."""
        session = self.get_session(session_id)
        if not session:
            return None
        try:
            return session.client.get_agent_progress(agent_id)
        except Exception:
            return None

    def get_agent_events(self, session_id: str, agent_id: str, since: int = 0) -> dict:
        """Get agent's execution events."""
        session = self.get_session(session_id)
        if not session:
            return {"agent_id": agent_id, "since": since, "count": 0, "events": []}
        try:
            return session.client.get_agent_events(agent_id, since=since)
        except Exception:
            return {"agent_id": agent_id, "since": since, "count": 0, "events": []}

    # ---- Custom tools ----

    def install_tool(self, session_id: str, spec: dict) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.install_tool(spec)

    def list_custom_tools(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.list_custom_tools()

    def remove_custom_tool(self, session_id: str, tool_name: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.remove_custom_tool(tool_name)

    # ---- Services ----

    def list_services(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.list_services()
        services = result.get("services", [])
        known = {str(s.get("port")): s for s in services}
        for container_port, host_port in session.service_ports.items():
            item = known.setdefault(container_port, {"port": int(container_port)})
            item["host_port"] = host_port
            item["url"] = f"http://localhost:{host_port}"
            item["status"] = "open" if self._is_port_open(host_port) else "closed"
        return {"services": list(known.values()), "service_ports": session.service_ports}

    def start_service(self, session_id: str, data: dict) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        port = int(data.get("port", 0) or 0)
        if port <= 0:
            raise ValueError("port required")
        if str(port) not in session.service_ports:
            raise ValueError(
                f"Port {port} is not exposed. Use one of: "
                + ", ".join(sorted(session.service_ports.keys()))
            )
        result = session.client.start_service(data)
        host_port = session.service_ports.get(str(port))
        if host_port:
            result["container_port"] = port
            result["host_port"] = host_port
            result["url"] = f"http://localhost:{host_port}"
        return result

    def stop_service(self, session_id: str, port: int) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.stop_service(port)

    def service_logs(self, session_id: str, port: int) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.service_logs(port)

    # ---- Internal ----

    def _wait_for_ready(self, port: int, timeout: int = 30):
        """Wait for orchestrator health check to pass."""
        client = OrchestratorClient(host="localhost", port=port)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = client.health_check()
                if resp.get("status") == "ok":
                    return
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError(f"Orchestrator did not become ready within {timeout}s")

    def _create_agent_in_container(self, port: int, config: dict):
        """Call orchestrator API to create an agent."""
        client = OrchestratorClient(host="localhost", port=port)
        client.create_agent(
            agent_id=config["agent_id"],
            role=config.get("role", "助手"),
            system_prompt=config.get("system_prompt", ""),
            workspace_name=config.get("workspace_name") or config.get("role") or config["agent_id"],
            adapter_name=config.get("adapter_name") or config.get("provider") or "claude",
        )

    @staticmethod
    def _recover_agents_from_labels(labels: dict) -> list[dict]:
        raw = labels.get("weagent.agents", "")
        if not raw:
            return []
        return json.loads(raw)

    @staticmethod
    def _find_free_port() -> int:
        """Find a random free port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @staticmethod
    def _is_port_open(port: int) -> bool:
        try:
            with socket.create_connection(("localhost", int(port)), timeout=0.3):
                return True
        except OSError:
            return False

    @staticmethod
    def _normalize_agent_user_input_path(agent_id: str, path: str,
                                         workspace_name: str = "") -> str:
        workspace_name = workspace_name or agent_id
        root = posixpath.normpath(f"/workspace/agents/{workspace_name}/userInput")
        normalized = "/" + str(path or "").replace("\\", "/").lstrip("/")
        normalized = posixpath.normpath(normalized)
        if normalized == root or not normalized.startswith(root + "/"):
            raise ValueError("Uploads and deletes must stay inside the agent userInput directory")
        return normalized

    @staticmethod
    def _workspace_name_for_agent(session: SessionContainer, agent_id: str) -> str:
        for agent in session.agents_config or []:
            if agent.get("agent_id") == agent_id:
                return agent.get("workspace_name") or agent.get("role") or agent_id
        return agent_id

    @staticmethod
    def _decode_exec_output(output) -> str:
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace").strip()
        return str(output or "").strip()

    def to_dict(self) -> dict:
        self.recover_sessions()
        return {
            "sessions": len(self._sessions),
            "image": self.image_name,
        }
