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
import mimetypes
import os
import posixpath
import re
import secrets
import socket
import tarfile
import threading
import time
import zipfile
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, urlparse

from .client import OrchestratorClient


# Lock for thread safety
_lock = threading.Lock()

_EXPORT_EXCLUDED_BASENAMES = {
    "CLAUDE.md",
    "agent.md",
    "config.json",
    "latest.txt",
    "meta.json",
    "previous.txt",
    "sandbox.log",
    "settings.local.json",
    "weagent-report.log",
}
_EXPORT_EXCLUDED_SUFFIXES = (".jsonl",)
_EXPORT_EXCLUDED_REGEXES = (
    re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$", re.IGNORECASE),
)
_MIGRATION_EXCLUDED_PARTS = {
    ".session",
    ".weagent",
    ".weagent_history",
    ".weagent_claude_session",
    "__pycache__",
    "node_modules",
    ".git",
}


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


def _merge_no_proxy(value: str = "") -> str:
    defaults = [
        "localhost",
        "127.0.0.1",
        "host.docker.internal",
        "gateway.docker.internal",
    ]
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    seen = {part.lower() for part in parts}
    for item in defaults:
        if item.lower() not in seen:
            parts.append(item)
            seen.add(item.lower())
    return ",".join(parts)


def _default_host_callback_url() -> str:
    return f"http://host.docker.internal:{os.getenv('PORT', '5002')}"


def _should_skip_export_member(path_parts: list[str]) -> bool:
    clean_parts = [part for part in path_parts if part not in {"", ".", ".."}]
    if not clean_parts:
        return True
    if any(part.startswith(".") for part in clean_parts):
        return True
    basename = clean_parts[-1]
    if basename in _EXPORT_EXCLUDED_BASENAMES:
        return True
    if basename.endswith(_EXPORT_EXCLUDED_SUFFIXES):
        return True
    return any(pattern.match(basename) for pattern in _EXPORT_EXCLUDED_REGEXES)


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
        self.service_tokens: dict[str, dict] = {}
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
            "HOST_CALLBACK_URL": env_vars.get("HOST_CALLBACK_URL") if env_vars and env_vars.get("HOST_CALLBACK_URL") else _default_host_callback_url(),
            "NO_PROXY": _merge_no_proxy(env_vars.get("NO_PROXY") if env_vars else os.environ.get("NO_PROXY", "")),
            "no_proxy": _merge_no_proxy(env_vars.get("no_proxy") if env_vars else os.environ.get("no_proxy", "")),
        }
        # Pass through provider env vars if provided. The container runners
        # translate these into each provider's private home/config.
        provider_env_keys = [
            "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
            "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
            "CODEX_API_KEY", "CODEX_BASE_URL", "CODEX_MODEL",
            "CODEX_AUTH_JSON", "CODEX_CONFIG_TOML", "CODEX_USE_RELAY",
            "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
            "API_TIMEOUT_MS", "CLAUDE_EXEC_TIMEOUT_SECONDS",
            "CODEX_EXEC_TIMEOUT_SECONDS", "OPENCODE_EXEC_TIMEOUT_SECONDS",
            "AGENT_EXEC_TIMEOUT_SECONDS",
            "RAG_INTERNAL_API_KEY", "RAG_SERVICE_URL",
            "RAG_SCOPE_USER_ID", "RAG_SCOPE_DOMAIN", "RAG_SCOPE_WORKSPACE_ID",
            "EDUCATION_RUN_GRANT", "EDUCATION_SERVICE_URL",
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
                        "EDUCATION_RUN_GRANT",
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
        self._project_capabilities_to_container(host_port, session_id, agents)

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
        session = self._sessions.get(session_id)
        if session is not None:
            return session
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
                agents_config = self._recover_agents_from_labels(container.labels)
            except Exception:
                agents_config = []
            if not agents_config:
                try:
                    info = OrchestratorClient(host="localhost", port=host_port).get_session_info()
                    agents_config = info.get("agents", [])
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
        result = session.client.send_to_agent(agent_id, message)
        self._sync_skill_drafts_from_result(session_id, result)
        return result

    def send_chain(self, session_id: str, messages: list[dict]) -> list[dict]:
        """Chain messages across agents."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] send_chain session_id={session_id} "
            f"message_count={len(messages or [])}"
        )
        result = session.client.send_chain(messages)
        self._sync_skill_drafts_from_result(session_id, result)
        return result

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
        result = session.client.delegate(message, moderator_id, target_agent_ids)
        self._sync_skill_drafts_from_result(session_id, result)
        return result

    def add_agent(self, session_id: str, config: dict) -> dict:
        """Add an agent to an existing session container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        print(
            f"[SandboxManager] add_agent session_id={session_id} "
            f"agent_id={config.get('agent_id')} role={config.get('role')}"
        )
        self._project_capabilities_to_container(
            session.host_port,
            session_id,
            [*session.agents_config, config],
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
        provider_keys = [
            "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
            "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
            "CODEX_API_KEY", "CODEX_BASE_URL", "CODEX_MODEL",
            "CODEX_AUTH_JSON", "CODEX_CONFIG_TOML", "CODEX_USE_RELAY",
            "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
        ]
        config["api_key"] = _clean_config_value(config["api_key"])
        config["base_url"] = _clean_base_url(config["base_url"])
        config["model"] = _clean_config_value(config["model"])
        for key in provider_keys:
            value = env_vars.get(key)
            if value is None:
                continue
            if key.endswith("BASE_URL"):
                config[key] = _clean_base_url(value)
            elif key.endswith("API_KEY") or key.endswith("AUTH_TOKEN") or key.endswith("MODEL"):
                config[key] = _clean_config_value(value)
            else:
                config[key] = value
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
        workspace_name = self._workspace_name_for_agent(session, agent_id)
        normalized_path = self._normalize_agent_workspace_path(agent_id, path, workspace_name)
        return self._read_workspace_file_from_container(session, normalized_path)

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

    def get_file_tree(self, session_id: str, root: str = "/workspace",
                      include_hidden: bool = False, max_depth: int = 8) -> dict:
        """Return the session workspace file tree."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        try:
            return self._build_workspace_tree_in_container(
                session,
                root=root,
                include_hidden=include_hidden,
                max_depth=max_depth,
            )
        except Exception:
            return session.client.list_file_tree(
                root=root,
                include_hidden=include_hidden,
                max_depth=max_depth,
            )

    def get_raw_file(self, session_id: str, path: str) -> tuple[bytes, str]:
        """Read a raw workspace file without requiring an agent id."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        normalized_path = "/" + str(path or "").replace("\\", "/").lstrip("/")
        normalized_path = posixpath.normpath(normalized_path)
        return self._read_workspace_file_from_container(session, normalized_path)

    def download_file(self, session_id: str, path: str) -> tuple[bytes, str, str]:
        """Read a workspace file for download."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        normalized_path = "/" + str(path or "").replace("\\", "/").lstrip("/")
        normalized_path = posixpath.normpath(normalized_path)
        if not normalized_path.startswith("/workspace/"):
            raise FileNotFoundError(path)

        try:
            content_bytes, mime_type = self._read_workspace_file_from_container(session, normalized_path)
            filename = posixpath.basename(normalized_path) or "download"
            encoded_name = quote(filename)
            disposition = f"attachment; filename=\"download\"; filename*=UTF-8''{encoded_name}"
            return content_bytes, mime_type, disposition
        except Exception:
            pass

        return session.client.download_file(normalized_path)

    def export_zip(self, session_id: str, path: str = "/workspace",
                   mode: str = "directory",
                   selected_paths: Optional[list[str]] = None) -> tuple[bytes, str, str]:
        """Export a workspace directory as a ZIP archive."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")

        normalized_path = "/" + str(path or "/workspace").replace("\\", "/").lstrip("/")
        normalized_path = posixpath.normpath(normalized_path)
        if normalized_path == "/workspace":
            export_path = normalized_path
        elif normalized_path.startswith("/workspace/"):
            export_path = normalized_path
        else:
            raise ValueError("Export path must be under /workspace/")

        try:
            container = self.docker.containers.get(session.container_id)
            stream, stat = container.get_archive(export_path)
            tar_bytes = b"".join(chunk for chunk in stream)
        except Exception as e:
            raise FileNotFoundError(export_path) from e

        tar_buffer = io.BytesIO(tar_bytes)
        zip_buffer = io.BytesIO()
        top_name = posixpath.basename(export_path.rstrip("/")) or "workspace"

        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar, zipfile.ZipFile(
            zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zip_file:
            members = tar.getmembers()
            member_names = [member.name.lstrip("./") for member in members]
            stat_is_dir = bool(stat.get("mode", 0) & 0o040000) if isinstance(stat, dict) else False
            inferred_is_dir = any(
                name == top_name or name.startswith(top_name.rstrip("/") + "/")
                for name in member_names
            ) and any("/" in name for name in member_names if name)
            is_dir = stat_is_dir or inferred_is_dir

            selected_relative_paths = None
            selected_relative_prefixes = None
            if selected_paths:
                if not is_dir:
                    raise ValueError("Selected export requires a directory path")
                selected_relative_paths = set()
                selected_relative_prefixes = set()
                for raw_path in selected_paths:
                    normalized_selected = "/" + str(raw_path or "").replace("\\", "/").lstrip("/")
                    normalized_selected = posixpath.normpath(normalized_selected)
                    if normalized_selected == export_path:
                        continue
                    if not normalized_selected.startswith(export_path.rstrip("/") + "/"):
                        raise ValueError("Selected export path must stay under the current directory")
                    relative_selected = posixpath.relpath(normalized_selected, export_path)
                    if relative_selected in {"", ".", ".."}:
                        continue
                    selected_relative_paths.add(relative_selected)
                    selected_relative_prefixes.add(relative_selected.rstrip("/") + "/")

            for member in members:
                if member.isdir() or member.issym() or member.islnk():
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                member_name = member.name.lstrip("./")
                if is_dir:
                    member_prefix = top_name.rstrip("/") + "/"
                    if member_name == top_name:
                        continue
                    if member_name.startswith(member_prefix):
                        relative_name = member_name[len(member_prefix):]
                    else:
                        relative_name = member_name
                else:
                    relative_name = posixpath.basename(member_name)
                path_parts = [part for part in relative_name.split("/") if part]
                if not path_parts:
                    continue
                if _should_skip_export_member(path_parts):
                    continue
                if selected_relative_paths is not None:
                    normalized_relative = "/".join(path_parts)
                    if normalized_relative not in selected_relative_paths and not any(
                        normalized_relative.startswith(prefix) for prefix in selected_relative_prefixes
                    ):
                        continue
                archive_name = posixpath.join(top_name, relative_name) if is_dir else relative_name
                zip_file.writestr(archive_name, extracted.read())

        zip_bytes = zip_buffer.getvalue()
        zip_name = f"{top_name}.zip"
        encoded_name = quote(zip_name)
        disposition = f"attachment; filename=\"export.zip\"; filename*=UTF-8''{encoded_name}"
        return zip_bytes, "application/zip", disposition

    def restore_zip(self, session_id: str, archive_bytes: bytes) -> dict:
        """Restore a trusted durable workspace snapshot into a fresh runtime."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        if not isinstance(archive_bytes, (bytes, bytearray)):
            raise ValueError("Snapshot archive must be bytes")

        restored = []
        total_size = 0
        with zipfile.ZipFile(io.BytesIO(bytes(archive_bytes)), "r") as archive:
            members = archive.infolist()
            if len(members) > 5000:
                raise ValueError("Snapshot archive contains too many files")
            for member in members:
                if member.is_dir():
                    continue
                raw_name = str(member.filename or "").replace("\\", "/").lstrip("/")
                normalized = posixpath.normpath(raw_name)
                if normalized in {"", ".", ".."} or normalized.startswith("../"):
                    raise ValueError("Snapshot archive contains an unsafe path")
                parts = [part for part in normalized.split("/") if part]
                if parts and parts[0] == "workspace":
                    parts = parts[1:]
                if not parts or any(part in {".", ".."} for part in parts):
                    continue
                target_path = "/workspace/" + "/".join(parts)
                content = archive.read(member)
                total_size += len(content)
                if total_size > 200 * 1024 * 1024:
                    raise ValueError("Snapshot expands beyond the restore limit")
                result = self.write_workspace_file(session_id, target_path, content)
                if result.get("status") != "ok":
                    raise RuntimeError(
                        result.get("error") or f"Failed to restore {target_path}"
                    )
                restored.append(target_path)
        return {"status": "ok", "restored_files": len(restored), "paths": restored}

    def write_workspace_file(self, session_id: str, file_path: str,
                             content_bytes: bytes) -> dict:
        """Write a file to any path under /workspace/ in the container."""
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")

        normalized_path = "/" + str(file_path or "").replace("\\", "/").lstrip("/")
        normalized_path = posixpath.normpath(normalized_path)
        if not normalized_path.startswith("/workspace/"):
            return {"status": "error", "error": "File path must be under /workspace/"}

        directory = posixpath.dirname(normalized_path)
        target_name = posixpath.basename(normalized_path)

        try:
            container = self.docker.containers.get(session.container_id)
            mkdir_result = container.exec_run(["mkdir", "-p", directory])
            if getattr(mkdir_result, "exit_code", 1) != 0:
                output = self._decode_exec_output(getattr(mkdir_result, "output", b""))
                return {"status": "error", "error": output or "Failed to create directory"}

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                info = tarfile.TarInfo(name=target_name)
                info.size = len(content_bytes)
                info.mtime = int(time.time())
                tar.addfile(info, io.BytesIO(content_bytes))
            tar_stream.seek(0)

            if not container.put_archive(directory, tar_stream.getvalue()):
                return {"status": "error", "error": "Failed to write file into container"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {"status": "ok", "path": normalized_path, "size": len(content_bytes)}

    def _read_workspace_file_from_container(self, session: SessionContainer,
                                            normalized_path: str) -> tuple[bytes, str]:
        normalized_path = "/" + str(normalized_path or "").replace("\\", "/").lstrip("/")
        normalized_path = posixpath.normpath(normalized_path)
        if not normalized_path.startswith("/workspace/"):
            raise FileNotFoundError(normalized_path)

        container = self.docker.containers.get(session.container_id)
        stream, _ = container.get_archive(normalized_path)
        tar_bytes = b"".join(chunk for chunk in stream)
        tar_buffer = io.BytesIO(tar_bytes)
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            for member in tar.getmembers():
                if member.isdir() or member.issym() or member.islnk():
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                content_bytes = extracted.read()
                filename = posixpath.basename(normalized_path) or posixpath.basename(member.name)
                mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                return content_bytes, mime_type
        raise FileNotFoundError(normalized_path)

    def _build_workspace_tree_in_container(self, session: SessionContainer, root: str = "/workspace",
                                           include_hidden: bool = False,
                                           max_depth: int = 8) -> dict:
        container = self.docker.containers.get(session.container_id)
        script = r"""
import json, mimetypes, os, sys

root = sys.argv[1] if len(sys.argv) > 1 else "/workspace"
include_hidden = (sys.argv[2].lower() == "true") if len(sys.argv) > 2 else False
max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 8

workspace_root = os.path.realpath("/workspace")
if root.startswith("/workspace"):
    full_path = root
else:
    full_path = os.path.join("/workspace", root.lstrip("/"))
real_root = os.path.realpath(full_path)
if real_root != workspace_root and not real_root.startswith(workspace_root + os.sep):
    print(json.dumps({"error": "Access denied: path outside workspace"}))
    raise SystemExit(0)
if not os.path.exists(real_root):
    print(json.dumps({"error": f"Path not found: {root}"}))
    raise SystemExit(0)

def build_node(path, depth):
    rel_path = os.path.relpath(path, workspace_root)
    node_path = "/workspace" if rel_path == "." else f"/workspace/{rel_path.replace(os.sep, '/')}"
    name = os.path.basename(path) or "workspace"
    if os.path.isdir(path):
        node = {"name": name, "path": node_path, "type": "directory", "children": []}
        if depth >= max_depth:
            node["truncated"] = True
            return node
        try:
            entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        except OSError:
            return node
        for entry in entries:
            if not include_hidden and entry.startswith("."):
                continue
            node["children"].append(build_node(os.path.join(path, entry), depth + 1))
        return node
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return {
        "name": name,
        "path": node_path,
        "type": "file",
        "size": size,
        "mime_type": mimetypes.guess_type(path)[0] or "application/octet-stream",
        "extension": os.path.splitext(path)[1].lstrip("."),
    }

print(json.dumps({"root": root, "tree": build_node(real_root, 0)}, ensure_ascii=False))
"""
        result = container.exec_run(
            ["python", "-c", script, root, "true" if include_hidden else "false", str(max_depth)]
        )
        if getattr(result, "exit_code", 1) != 0:
            output = self._decode_exec_output(getattr(result, "output", b""))
            raise RuntimeError(output or "Failed to build workspace tree")
        output = self._decode_exec_output(getattr(result, "output", b""))
        return json.loads(output or "{}")

    def preview_files_between_sessions(
        self,
        source_session_id: str,
        target_session_id: str,
        root: str = "/workspace/agents",
        paths: Optional[list[str]] = None,
        path_mapping: Optional[dict[str, str]] = None,
        overwrite: bool = False,
        include_hidden: bool = False,
    ) -> dict:
        source_session = self.get_session(source_session_id)
        if not source_session:
            raise KeyError(f"Session '{source_session_id}' not found")
        target_session = self.get_session(target_session_id)
        if not target_session:
            raise KeyError(f"Session '{target_session_id}' not found")

        normalized_root = self._normalize_workspace_path(root, allowed_root="/workspace/agents")
        selected_paths = [
            self._normalize_workspace_path(item, allowed_root=normalized_root)
            for item in (paths or [])
        ]
        candidate_paths, skipped = self._collect_migration_candidates(
            source_session,
            normalized_root,
            selected_paths or None,
            include_hidden=include_hidden,
        )
        resolved_mapping = self._resolve_migration_path_mapping(
            source_session,
            target_session,
            candidate_paths,
            path_mapping=path_mapping,
        )

        conflicts = []
        for source_path in candidate_paths:
            target_path = self._map_target_path(source_path, resolved_mapping)
            if not overwrite and self._target_path_exists(target_session, target_path):
                conflicts.append({
                    "source_path": source_path,
                    "target_path": target_path,
                    "reason": "target exists and overwrite=false",
                })

        return {
            "source_session_id": source_session_id,
            "target_session_id": target_session_id,
            "root": normalized_root,
            "total_candidates": len(candidate_paths),
            "path_mapping": resolved_mapping,
            "conflicts": conflicts,
            "skipped": skipped,
        }

    def copy_files_between_sessions(
        self,
        source_session_id: str,
        target_session_id: str,
        root: str = "/workspace/agents",
        paths: Optional[list[str]] = None,
        path_mapping: Optional[dict[str, str]] = None,
        overwrite: bool = False,
        include_hidden: bool = False,
    ) -> dict:
        started_at = time.perf_counter()
        source_session = self.get_session(source_session_id)
        if not source_session:
            raise KeyError(f"Session '{source_session_id}' not found")
        target_session = self.get_session(target_session_id)
        if not target_session:
            raise KeyError(f"Session '{target_session_id}' not found")

        preview = self.preview_files_between_sessions(
            source_session_id=source_session_id,
            target_session_id=target_session_id,
            root=root,
            paths=paths,
            path_mapping=path_mapping,
            overwrite=overwrite,
            include_hidden=include_hidden,
        )
        candidate_paths, skipped = self._collect_migration_candidates(
            source_session,
            preview["root"],
            [
                self._normalize_workspace_path(item, allowed_root=preview["root"])
                for item in (paths or [])
            ] or None,
            include_hidden=include_hidden,
        )
        conflicts = list(preview.get("conflicts") or [])
        conflict_sources = {item["source_path"] for item in conflicts}
        resolved_mapping = preview["path_mapping"]
        errors = []
        migrated = 0
        skipped_items = list(skipped)

        for source_path in candidate_paths:
            target_path = self._map_target_path(source_path, resolved_mapping)
            if source_path in conflict_sources:
                continue
            try:
                self._copy_one_path_between_sessions(
                    source_session,
                    target_session,
                    source_path,
                    target_path,
                )
                migrated += 1
            except Exception as exc:
                errors.append({
                    "source_path": source_path,
                    "target_path": target_path,
                    "reason": str(exc),
                })

        return {
            "source_session_id": source_session_id,
            "target_session_id": target_session_id,
            "root": preview["root"],
            "total_candidates": len(candidate_paths),
            "migrated": migrated,
            "skipped": len(skipped_items),
            "skipped_items": skipped_items,
            "errors": errors,
            "conflicts": conflicts,
            "path_mapping": resolved_mapping,
            "message": f"migrated {migrated} files, skipped {len(skipped_items)} files",
            "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
        }

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

    # ---- MCP ----

    def list_mcp_servers(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.list_mcp_servers()

    def start_mcp_server(self, session_id: str, agent_id: str, runtime_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.start_mcp_server(agent_id, runtime_id)

    def list_mcp_tools(self, session_id: str, runtime_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.list_mcp_tools(runtime_id)

    def call_mcp_tool(self, session_id: str, agent_id: str, runtime_id: str,
                      tool_name: str, args: dict) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.call_mcp_tool(agent_id, runtime_id, tool_name, args)

    def stop_mcp_server(self, session_id: str, runtime_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.stop_mcp_server(runtime_id)

    # ---- Services ----

    def list_services(self, session_id: str, user_id: str | None = None) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.list_services()
        result.setdefault("services", [])
        for service in result["services"]:
            self._attach_service_proxy_url(session, service, user_id=user_id)
        result["session_id"] = session_id
        return result

    def start_service(self, session_id: str, data: dict, user_id: str | None = None) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        port = int(data.get("port", 0) or 0)
        if port <= 0:
            raise ValueError("port required")
        result = session.client.start_service(data)
        self._attach_service_proxy_url(session, result.get("service"), user_id=user_id)
        result["session_id"] = session_id
        return result

    def get_service(self, session_id: str, service_id: str, user_id: str | None = None) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.get_service(service_id)
        self._attach_service_proxy_url(session, result.get("service"), user_id=user_id)
        return result

    def stop_service(self, session_id: str, service_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.stop_service(service_id)
        self._attach_service_proxy_url(session, result.get("service"))
        return result

    def restart_service(self, session_id: str, service_id: str, user_id: str | None = None) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        result = session.client.restart_service(service_id)
        self._attach_service_proxy_url(session, result.get("service"), user_id=user_id)
        return result

    def service_logs(self, session_id: str, service_id: str, tail_bytes: int = 65536) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.service_logs(service_id, tail_bytes=tail_bytes)

    def proxy_service(
        self,
        session_id: str,
        service_id: str,
        path: str,
        method: str,
        headers: dict | None = None,
        body: bytes | None = None,
        query_string: str = "",
    ) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.proxy_service(
            service_id=service_id,
            path=path,
            method=method,
            headers=headers,
            body=body,
            query_string=query_string,
        )

    def proxy_service_websocket(
        self,
        session_id: str,
        service_id: str,
        path: str,
        client_ws,
        headers: dict | None = None,
        query_string: str = "",
    ) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.client.proxy_service_websocket(
            service_id=service_id,
            path=path,
            client_ws=client_ws,
            headers=headers,
            query_string=query_string,
        )

    def refresh_service_token(
        self,
        session_id: str,
        service_id: str,
        user_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        service_result = session.client.get_service(service_id)
        if service_result.get("error"):
            return service_result
        ttl = self._service_token_ttl(ttl_seconds)
        token = secrets.token_urlsafe(32)
        expires_at_ts = time.time() + ttl
        session.service_tokens[service_id] = {
            "token": token,
            "session_id": session_id,
            "service_id": service_id,
            "user_id": user_id or "",
            "created_at": self._iso_time(time.time()),
            "expires_at": self._iso_time(expires_at_ts),
            "expires_at_ts": expires_at_ts,
        }
        service = service_result.get("service")
        self._attach_service_proxy_url(session, service, token=token)
        return {
            "status": "ok",
            "token": token,
            "expires_at": session.service_tokens[service_id]["expires_at"],
            "expires_in": ttl,
            "proxy_url": self._service_proxy_url(session_id, service_id, token=token),
            "service": service,
        }

    def validate_service_token(self, session_id: str, service_id: str, token: str | None) -> bool:
        if not token:
            return False
        session = self.get_session(session_id)
        if not session:
            return False
        meta = session.service_tokens.get(service_id)
        if not meta or meta.get("token") != token:
            return False
        if float(meta.get("expires_at_ts") or 0) <= time.time():
            session.service_tokens.pop(service_id, None)
            return False
        return meta.get("session_id") == session_id and meta.get("service_id") == service_id

    def _attach_service_proxy_url(
        self,
        session: SessionContainer,
        service: dict | None,
        user_id: str | None = None,
        token: str | None = None,
    ) -> None:
        if not isinstance(service, dict) or not service.get("id"):
            return
        service_id = service["id"]
        token = token or self._ensure_service_token(session, service_id, user_id=user_id)
        proxy_url = self._service_proxy_url(session.session_id, service_id, token=token)
        service["proxy_url"] = proxy_url
        service["url"] = proxy_url
        token_meta = session.service_tokens.get(service_id) or {}
        if token_meta.get("expires_at"):
            service["preview_token_expires_at"] = token_meta["expires_at"]

    def _ensure_service_token(
        self,
        session: SessionContainer,
        service_id: str,
        user_id: str | None = None,
    ) -> str:
        meta = session.service_tokens.get(service_id)
        if meta and float(meta.get("expires_at_ts") or 0) > time.time():
            return str(meta["token"])
        result = self.refresh_service_token(
            session.session_id,
            service_id,
            user_id=user_id,
        )
        return str(result.get("token") or "")

    @staticmethod
    def _service_proxy_url(session_id: str, service_id: str, token: str | None = None) -> str:
        url = f"/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/"
        if token:
            url += f"?token={token}"
        return url

    @staticmethod
    def _service_token_ttl(ttl_seconds: int | None = None) -> int:
        if ttl_seconds is None:
            ttl_seconds = int(os.environ.get("SANDBOX_SERVICE_TOKEN_TTL_SECONDS", "7200"))
        return max(60, min(int(ttl_seconds), 24 * 60 * 60))

    @staticmethod
    def _iso_time(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

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
        result = client.create_agent(
            agent_id=config["agent_id"],
            role=config.get("role", "助手"),
            system_prompt=config.get("system_prompt", ""),
            workspace_name=config.get("workspace_name") or config.get("role") or config["agent_id"],
            adapter_name=config.get("adapter_name") or config.get("provider") or "claude",
        )
        if result.get("status") not in {"ok", None} or result.get("error"):
            raise RuntimeError(result.get("error") or "Failed to create agent in sandbox container")
        return result

    def _project_capabilities_to_container(self, port: int, session_id: str,
                                           agents: list[dict]) -> dict:
        """Build DB-backed capability projection and install it before agent startup."""
        from app.services.capability_projection_service import build_capability_projection

        projection = build_capability_projection(session_id=session_id, agents=agents)
        client = OrchestratorClient(host="localhost", port=port)
        result = client.apply_capability_projection(projection)
        if self._is_missing_optional_orchestrator_route(result):
            print(
                "[SandboxManager] capability_projection_skipped "
                f"session_id={session_id} reason=container_route_not_found"
            )
            return projection
        if result.get("status") not in {"ok", None} or result.get("error"):
            raise RuntimeError(result.get("error") or "Failed to apply capability projection")
        return projection

    @staticmethod
    def _is_missing_optional_orchestrator_route(result: dict) -> bool:
        if not isinstance(result, dict):
            return False
        error = str(result.get("error") or "")
        return bool(result.get("optional_route_missing")) or (
            result.get("status") == "error" and "HTTP 404" in error and "Not Found" in error
        )

    def _sync_skill_drafts_from_result(self, session_id: str, result):
        drafts = self._extract_skill_drafts(result)
        if not drafts:
            return
        try:
            from app.models.conversation import Conversation
            from app.services.capability_draft_sync_service import (
                capability_draft_sync_service,
            )

            conversation = Conversation.query.get(session_id)
            if not conversation:
                return
            synced, error = capability_draft_sync_service.sync_records(
                user_id=conversation.owner_id,
                records=drafts,
            )
            if isinstance(result, dict):
                if error:
                    result["skill_drafts_sync"] = {"status": "error", "error": error}
                else:
                    result["skill_drafts_sync"] = {
                        "status": "ok",
                        "count": len(synced or []),
                    }
        except Exception as exc:
            if isinstance(result, dict):
                result["skill_drafts_sync"] = {
                    "status": "error",
                    "error": str(exc),
                }

    def _extract_skill_drafts(self, result) -> list[dict]:
        drafts = []
        if isinstance(result, dict):
            if isinstance(result.get("skill_drafts"), list):
                drafts.extend(result["skill_drafts"])
            nested = result.get("results")
            if isinstance(nested, list):
                for item in nested:
                    drafts.extend(self._extract_skill_drafts(item))
        elif isinstance(result, list):
            for item in result:
                drafts.extend(self._extract_skill_drafts(item))
        return drafts

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
    def _normalize_agent_workspace_path(agent_id: str, path: str,
                                        workspace_name: str = "") -> str:
        workspace_name = workspace_name or agent_id
        root = posixpath.normpath(f"/workspace/agents/{workspace_name}")
        normalized = "/" + str(path or "").replace("\\", "/").lstrip("/")
        normalized = posixpath.normpath(normalized)
        if normalized == root or normalized.startswith(root + "/"):
            return normalized
        raise ValueError("Path must stay inside the agent workspace directory")

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

    @staticmethod
    def _normalize_workspace_path(path: str, allowed_root: str = "/workspace") -> str:
        normalized = "/" + str(path or "").replace("\\", "/").lstrip("/")
        normalized = posixpath.normpath(normalized)
        allowed = posixpath.normpath(allowed_root or "/workspace")
        if allowed == "/workspace":
            if normalized != allowed and not normalized.startswith(allowed + "/"):
                raise ValueError("Path must stay under /workspace/")
            return normalized
        if normalized != allowed and not normalized.startswith(allowed + "/"):
            raise ValueError(f"Path must stay under {allowed}")
        return normalized

    def _collect_migration_candidates(
        self,
        source_session: SessionContainer,
        root: str,
        selected_paths: Optional[list[str]] = None,
        include_hidden: bool = False,
    ) -> tuple[list[str], list[dict]]:
        paths = selected_paths or [root]
        candidates: list[str] = []
        skipped: list[dict] = []
        seen: set[str] = set()

        def walk(node):
            if not isinstance(node, dict):
                return
            node_path = self._normalize_workspace_path(node.get("path") or root, allowed_root="/workspace")
            if self._should_exclude_migration_path(node_path, include_hidden=include_hidden):
                skipped.append({"source_path": node_path, "reason": "excluded path"})
                return
            if node.get("type") == "directory":
                children = node.get("children") or []
                if not children:
                    skipped.append({"source_path": node_path, "reason": "empty directory"})
                    return
                for child in children:
                    walk(child)
                return
            if node_path not in seen:
                seen.add(node_path)
                candidates.append(node_path)

        for path in paths:
            tree_result = self.get_file_tree(
                source_session.session_id,
                root=path,
                include_hidden=include_hidden,
                max_depth=32,
            )
            if tree_result.get("error"):
                raise ValueError(tree_result["error"])
            tree = tree_result.get("tree")
            if not tree:
                skipped.append({"source_path": path, "reason": "path has no readable tree"})
                continue
            walk(tree)

        return candidates, skipped

    def _resolve_migration_path_mapping(
        self,
        source_session: SessionContainer,
        target_session: SessionContainer,
        candidate_paths: list[str],
        path_mapping: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        provided = {}
        for source_prefix, target_prefix in (path_mapping or {}).items():
            normalized_source = self._normalize_workspace_path(source_prefix, allowed_root="/workspace/agents")
            normalized_target = self._normalize_workspace_path(target_prefix, allowed_root="/workspace/agents")
            provided[normalized_source] = normalized_target

        target_workspaces = {
            str(agent.get("workspace_name") or agent.get("role") or agent.get("agent_id") or ""): agent
            for agent in (target_session.agents_config or [])
        }
        resolved: dict[str, str] = {}

        for source_path in candidate_paths:
            source_prefix = self._source_workspace_prefix(source_path)
            if not source_prefix or source_prefix in resolved:
                continue
            if source_prefix in provided:
                resolved[source_prefix] = provided[source_prefix]
                continue
            workspace_name = source_prefix.split("/")[3] if len(source_prefix.split("/")) > 3 else ""
            if workspace_name and self._is_ascii_name(workspace_name) and workspace_name in target_workspaces:
                resolved[source_prefix] = f"/workspace/agents/{workspace_name}"
            else:
                resolved[source_prefix] = (
                    f"/workspace/agents/migrated_from_{source_session.session_id[:8]}/{workspace_name or 'workspace'}"
                )
        return resolved

    @staticmethod
    def _source_workspace_prefix(source_path: str) -> str:
        parts = [part for part in str(source_path or "").split("/") if part]
        if len(parts) >= 3 and parts[0] == "workspace" and parts[1] == "agents":
            return f"/workspace/agents/{parts[2]}"
        return ""

    @staticmethod
    def _is_ascii_name(text: str) -> bool:
        try:
            str(text or "").encode("ascii")
            return True
        except UnicodeEncodeError:
            return False

    @staticmethod
    def _map_target_path(source_path: str, resolved_mapping: dict[str, str]) -> str:
        normalized_source = "/" + str(source_path or "").replace("\\", "/").lstrip("/")
        normalized_source = posixpath.normpath(normalized_source)
        for source_prefix in sorted(resolved_mapping.keys(), key=len, reverse=True):
            if normalized_source == source_prefix or normalized_source.startswith(source_prefix + "/"):
                suffix = normalized_source[len(source_prefix):].lstrip("/")
                target_prefix = resolved_mapping[source_prefix].rstrip("/")
                return target_prefix if not suffix else f"{target_prefix}/{suffix}"
        return normalized_source

    @staticmethod
    def _should_exclude_migration_path(path: str, include_hidden: bool = False) -> bool:
        parts = [part for part in str(path or "").split("/") if part]
        if not include_hidden and any(part.startswith(".") for part in parts):
            return True
        return any(part in _MIGRATION_EXCLUDED_PARTS for part in parts)

    def _target_path_exists(self, target_session: SessionContainer, target_path: str) -> bool:
        normalized = self._normalize_workspace_path(target_path, allowed_root="/workspace")
        container = self.docker.containers.get(target_session.container_id)
        result = container.exec_run([
            "python",
            "-c",
            "import os, sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)",
            normalized,
        ])
        return getattr(result, "exit_code", 1) == 0

    def _copy_one_path_between_sessions(
        self,
        source_session: SessionContainer,
        target_session: SessionContainer,
        source_path: str,
        target_path: str,
    ) -> None:
        normalized_source = self._normalize_workspace_path(source_path, allowed_root="/workspace")
        normalized_target = self._normalize_workspace_path(target_path, allowed_root="/workspace")
        content_bytes, _ = self._read_workspace_file_from_container(source_session, normalized_source)
        result = self.write_workspace_file(target_session.session_id, normalized_target, content_bytes)
        if result.get("status") == "error":
            raise RuntimeError(result.get("error") or "Failed to write target file")

    def _is_empty_directory(self, session: SessionContainer, path: str) -> bool:
        normalized = self._normalize_workspace_path(path, allowed_root="/workspace")
        container = self.docker.containers.get(session.container_id)
        result = container.exec_run([
            "python",
            "-c",
            (
                "import os, sys; "
                "p=sys.argv[1]; "
                "sys.exit(0 if os.path.isdir(p) and len(os.listdir(p))==0 else 1)"
            ),
            normalized,
        ])
        return getattr(result, "exit_code", 1) == 0

    def to_dict(self) -> dict:
        self.recover_sessions()
        return {
            "sessions": len(self._sessions),
            "image": self.image_name,
        }
