from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from urllib.parse import urlparse

from .base import ProviderRunner
from .json_stream import JsonObjectStream, extract_text_value, is_internal_plain_line
from ..capabilities import _safe_segment
from ..logging_utils import log_agent


class CodexRunner(ProviderRunner):
    provider_name = "codex"
    display_name = "Codex"
    log_prefix = "codex"
    timeout_env_var = "CODEX_EXEC_TIMEOUT_SECONDS"
    default_timeout_seconds = 600

    @property
    def provider_dir(self) -> str:
        return f"{self.runtime._agent_dir}/.weagent/providers/codex"

    @property
    def home_dir(self) -> str:
        return f"{self.provider_dir}/home"

    @property
    def resume_marker(self) -> str:
        return f"{self.provider_dir}/session_marker"

    def setup(self) -> None:
        os.makedirs(self.home_dir, exist_ok=True)
        self._preflight_error = ""
        self._relay_process = None
        self._relay_upstream = ""
        self._relay_base_url = ""
        self._write_noninteractive_config()
        self._stream_parser = JsonObjectStream()

    def build_command(self, message: str, retry_with_resume: bool = True) -> tuple[list[str], bool]:
        runtime = self.runtime
        full_message = f"{runtime._runtime_instruction()}\n\n用户任务：\n{message}"
        use_resume = retry_with_resume and os.path.exists(self.resume_marker)
        if use_resume:
            cmd = [
                "codex",
                "exec",
                "resume",
                "--last",
                "--json",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                full_message,
            ]
        else:
            cmd = [
                "codex",
                "exec",
                "--json",
                "--cd",
                runtime._agent_dir,
                "--sandbox",
                "workspace-write",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                full_message,
            ]
        return cmd, use_resume

    def environment(self) -> dict:
        runtime = self.runtime
        self._init_relay_state()
        env = os.environ.copy()
        api_key = self._first_env(
            "CODEX_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        )
        base_url = self._codex_base_url()
        provider_name = self._provider_name(base_url)
        base_url = self._codex_runtime_base_url(base_url, provider_name)
        model = self._first_env("CODEX_MODEL", "OPENAI_MODEL", "DEEPSEEK_MODEL", "ANTHROPIC_MODEL")
        env.update({
            "CODEX_HOME": self.home_dir,
            "WEAGENT_AGENT_ID": runtime.agent_id,
            "WEAGENT_WORKSPACE_NAME": runtime.workspace_name,
            "NO_COLOR": "1",
            "CI": "1",
        })
        if api_key:
            env["OPENAI_API_KEY"] = api_key
            env["CODEX_API_KEY"] = api_key
        if base_url:
            env["OPENAI_BASE_URL"] = base_url
            env["CODEX_BASE_URL"] = base_url
        if model:
            env["OPENAI_MODEL"] = model
            env["CODEX_MODEL"] = model
        return env

    @property
    def runnable(self) -> bool:
        return not getattr(self, "_preflight_error", "")

    def unavailable_message(self) -> str:
        return getattr(self, "_preflight_error", "") or super().unavailable_message()

    def clean_output(self, stdout: str) -> str:
        return self._parse_output(stdout, final=True)

    def stream_chunk(self, chunk: str, stream_name: str) -> str:
        if stream_name != "stdout":
            return chunk
        return self._parse_stream_chunk(chunk)

    def _parse_output(self, text: str, final: bool = False) -> str:
        parser = JsonObjectStream()
        items = parser.feed_items(text or "", final=True)
        parts = self._visible_parts(items, include_status=final)
        return "\n".join(parts).strip()

    def _parse_stream_chunk(self, chunk: str) -> str:
        parser = getattr(self, "_stream_parser", None)
        if parser is None:
            parser = self._stream_parser = JsonObjectStream()
        items = parser.feed_items(chunk or "", final=False)
        parts = self._visible_parts(items, include_status=False)
        return "\n".join(parts) + ("\n" if parts else "")

    def _visible_parts(self, items: list[tuple[str, object]], include_status: bool) -> list[str]:
        parts = []
        for item_type, value in items:
            if item_type == "plain":
                line = str(value)
                if not is_internal_plain_line(line):
                    parts.append(line)
            elif isinstance(value, dict):
                text = self._extract_text(value, include_status=include_status)
                if text:
                    parts.append(text)
        return parts

    def should_retry_without_resume(self, stderr: str) -> bool:
        text = (stderr or "").lower()
        markers = (
            "no previous session",
            "no conversation",
            "session not found",
            "not found",
            "failed to resume",
            "unable to resume",
        )
        return any(marker in text for marker in markers)

    def clear_resume_state(self) -> None:
        try:
            os.remove(self.resume_marker)
        except OSError:
            pass

    def mark_success(self) -> None:
        os.makedirs(self.provider_dir, exist_ok=True)
        try:
            with open(self.resume_marker, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except OSError as exc:
            log_agent(
                self.runtime.agent_id,
                "codex_session_marker_failed",
                level="warning",
                role=self.runtime.role,
                error=str(exc),
            )

    def is_auth_error(self, output: str) -> bool:
        text = output or ""
        return any(marker in text for marker in (
            "OPENAI_API_KEY",
            "not logged in",
            "authentication",
            "api key",
        ))

    def auth_error_message(self, output: str) -> str:
        return (
            "[AuthError] Codex authentication failed. Provide CODEX_API_KEY or OPENAI_API_KEY; "
            "for DeepSeek, provide DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL and DEEPSEEK_MODEL. "
            f"Raw error: {output}"
        )

    def context_log_fields(self, used_resume: bool) -> dict:
        return {
            "use_resume": used_resume,
            "marker": self.resume_marker,
            "codex_home": self.home_dir,
        }

    def started_payload(self) -> dict:
        payload = super().started_payload()
        payload["provider"] = self.provider_name
        return payload

    def _write_noninteractive_config(self) -> None:
        self._init_relay_state()
        auth_json = self._first_env("CODEX_AUTH_JSON")
        config_toml = self._first_env("CODEX_CONFIG_TOML")
        api_key = self._first_env(
            "CODEX_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        )
        model = self._first_env("CODEX_MODEL", "OPENAI_MODEL", "DEEPSEEK_MODEL", "ANTHROPIC_MODEL")
        base_url = self._codex_base_url()
        provider_name = self._provider_name(base_url)
        config_base_url = self._codex_config_base_url(base_url, provider_name)

        if config_toml:
            self._write_file("config.toml", config_toml.strip() + "\n")
        else:
            self._write_file("config.toml", self._build_config_toml(provider_name, model, config_base_url))

        if auth_json:
            try:
                parsed = json.loads(auth_json)
                self._write_file("auth.json", json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", mode=0o600)
            except Exception as exc:
                self._preflight_error = f"Invalid CODEX_AUTH_JSON: {exc}"
        elif api_key:
            self._write_file(
                "auth.json",
                json.dumps({"OPENAI_API_KEY": api_key}, ensure_ascii=False, indent=2) + "\n",
                mode=0o600,
            )

        if not self._has_auth_file() and not api_key:
            self._preflight_error = (
                "Codex is not authenticated in the sandbox. Set CODEX_API_KEY or OPENAI_API_KEY. "
                "For DeepSeek-compatible runs, set DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL and DEEPSEEK_MODEL."
            )

        log_agent(
            self.runtime.agent_id,
            "codex_config_prepared",
            role=self.runtime.role,
            codex_home=self.home_dir,
            model=model or "",
            base_url=config_base_url or "",
            upstream_base_url=base_url or "",
            provider_name=provider_name,
            use_relay=self._uses_relay(provider_name, base_url),
            has_auth=self._has_auth_file() or bool(api_key),
            preflight_error=bool(self._preflight_error),
        )

    def _build_config_toml(self, provider_name: str, model: str, base_url: str) -> str:
        lines = [
            'approval_policy = "never"',
            'sandbox_mode = "danger-full-access"',
            'disable_response_storage = true',
        ]
        if model:
            lines.append(f"model = {self._toml_string(model)}")
        if base_url:
            lines.extend([
                f"model_provider = {self._toml_string(provider_name)}",
                "",
                f"[model_providers.{provider_name}]",
                f"name = {self._toml_string(provider_name)}",
                'wire_api = "responses"',
                "requires_openai_auth = true",
                f"base_url = {self._toml_string(base_url)}",
            ])
        for server in self._bound_mcp_servers():
            lines.extend([
                "",
                f"[mcp_servers.{server['config_name']}]",
                f"command = {self._toml_string(server['command'])}",
                f"args = {json.dumps(server['args'], ensure_ascii=False)}",
            ])
        return "\n".join(lines).strip() + "\n"

    def _bound_mcp_servers(self) -> list[dict]:
        capabilities_path = os.path.join(
            self._workspace_root(),
            ".weagent",
            "agents",
            _safe_segment(self.runtime.agent_id),
            "capabilities.json",
        )
        try:
            with open(capabilities_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return []

        servers = []
        used_names = set()
        for capability in payload.get("capabilities") or []:
            if capability.get("type") != "mcp":
                continue
            manifest = capability.get("manifest") or {}
            raw = manifest.get("raw") if isinstance(manifest.get("raw"), dict) else {}
            entry = manifest.get("entry") or raw.get("entry") or {}
            command = entry.get("command")
            args = entry.get("args") or []
            if not isinstance(command, str) or not command.strip():
                continue
            if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
                continue
            base_name = self._codex_mcp_server_name(
                capability.get("name")
                or capability.get("source_ref")
                or capability.get("runtime_id")
                or capability.get("capability_id")
            )
            config_name = base_name
            suffix = 2
            while config_name in used_names:
                config_name = f"{base_name}_{suffix}"
                suffix += 1
            used_names.add(config_name)
            servers.append({
                "config_name": config_name,
                "command": command.strip(),
                "args": args,
            })
        return servers

    @staticmethod
    def _workspace_root() -> str:
        return os.environ.get("WEAGENT_WORKSPACE_ROOT", "/workspace")

    @staticmethod
    def _codex_mcp_server_name(value: str) -> str:
        text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip().lower())
        text = re.sub(r"_+", "_", text).strip("_-")
        return text[:64] or "weagent_mcp"

    def _write_file(self, filename: str, content: str, mode: int = 0o644) -> None:
        path = os.path.join(self.home_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            os.chmod(path, mode)
        except OSError:
            pass

    def _has_auth_file(self) -> bool:
        return os.path.exists(os.path.join(self.home_dir, "auth.json"))

    def _codex_base_url(self) -> str:
        base_url = self._first_env("CODEX_BASE_URL", "OPENAI_BASE_URL")
        if base_url:
            return self._codex_upstream_base_url(base_url)
        deepseek_base = self._first_env("DEEPSEEK_BASE_URL")
        if deepseek_base:
            return self._codex_upstream_base_url(deepseek_base)
        anthropic_base = self._first_env("ANTHROPIC_BASE_URL")
        if anthropic_base:
            return self._codex_upstream_base_url(anthropic_base)
        return ""

    @classmethod
    def _codex_upstream_base_url(cls, base_url: str) -> str:
        cleaned = cls._clean_base_url(base_url)
        parsed = urlparse(cleaned)
        host = parsed.netloc.lower()
        if "deepseek" in host and cleaned.endswith("/anthropic"):
            return cleaned[:-len("/anthropic")] + "/v1"
        if "deepseek" in host and "/anthropic/" in cleaned:
            return cleaned.replace("/anthropic/", "/v1/", 1)
        return cleaned

    def _codex_config_base_url(self, upstream_base_url: str, provider_name: str) -> str:
        if self._uses_relay(provider_name, upstream_base_url):
            return self._ensure_relay(upstream_base_url)
        return upstream_base_url

    def _codex_runtime_base_url(self, upstream_base_url: str, provider_name: str) -> str:
        if self._uses_relay(provider_name, upstream_base_url):
            return getattr(self, "_relay_base_url", "") or self._ensure_relay(upstream_base_url)
        return upstream_base_url

    @staticmethod
    def _uses_relay(provider_name: str, base_url: str) -> bool:
        forced = CodexRunner._first_env("CODEX_USE_RELAY")
        if forced.lower() in {"0", "false", "no", "off"}:
            return False
        if forced.lower() in {"1", "true", "yes", "on"}:
            return True
        host = urlparse(base_url or "").netloc.lower()
        return provider_name == "deepseek" or "deepseek" in host

    def _ensure_relay(self, upstream_base_url: str) -> str:
        self._init_relay_state()
        if self._relay_base_url and self._relay_upstream == upstream_base_url:
            return self._relay_base_url
        port = self._first_free_port()
        relay_base_url = f"http://127.0.0.1:{port}/v1"
        log_path = os.path.join(self.provider_dir, "codex-relay.log")
        os.makedirs(self.provider_dir, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "CODEX_RELAY_HOST": "127.0.0.1",
            "CODEX_RELAY_PORT": str(port),
            "CODEX_RELAY_UPSTREAM": upstream_base_url,
            "CODEX_RELAY_API_KEY": self._first_env(
                "DEEPSEEK_API_KEY",
                "CODEX_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
            ),
            "CODEX_RELAY_BIND": f"127.0.0.1:{port}",
            "CODEX_RELAY_ADDR": f"127.0.0.1:{port}",
            "NO_COLOR": "1",
        })
        log_file = open(log_path, "a", encoding="utf-8")
        try:
            self._relay_process = subprocess.Popen(
                ["codex-relay"],
                cwd=self.runtime._agent_dir,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=log_file,
                env=env,
                text=True,
            )
        except FileNotFoundError:
            self._preflight_error = (
                "codex-relay is required for Codex + DeepSeek, but it is not installed in the sandbox image."
            )
            return relay_base_url
        except Exception as exc:
            self._preflight_error = f"Failed to start codex-relay for DeepSeek: {exc}"
            return relay_base_url
        finally:
            try:
                log_file.close()
            except Exception:
                pass
        self._relay_upstream = upstream_base_url
        self._relay_base_url = relay_base_url
        log_agent(
            self.runtime.agent_id,
            "codex_relay_started",
            role=self.runtime.role,
            upstream=upstream_base_url,
            base_url=relay_base_url,
            pid=getattr(self._relay_process, "pid", None),
            log_path=log_path,
        )
        return relay_base_url

    def _init_relay_state(self) -> None:
        if not hasattr(self, "_relay_process"):
            self._relay_process = None
        if not hasattr(self, "_relay_upstream"):
            self._relay_upstream = ""
        if not hasattr(self, "_relay_base_url"):
            self._relay_base_url = ""

    @staticmethod
    def _first_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _provider_name(base_url: str) -> str:
        host = urlparse(base_url or "").netloc.lower()
        if "deepseek" in host:
            return "deepseek"
        if "openai" in host:
            return "openai"
        return "openai_compatible"

    @staticmethod
    def _first_env(*keys: str) -> str:
        for key in keys:
            value = os.environ.get(key)
            if value:
                text = str(value).strip().strip(" \t\r\n'\"")
                if text:
                    return text
        return ""

    @staticmethod
    def _clean_base_url(value: str) -> str:
        text = str(value or "").strip().strip(" \t\r\n'\"").rstrip("/")
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid base URL: {text}")
        return text

    @staticmethod
    def _toml_string(value: str) -> str:
        return json.dumps(str(value or ""), ensure_ascii=False)

    @staticmethod
    def _extract_text(event: dict, include_status: bool = False) -> str:
        if not isinstance(event, dict):
            return ""
        event_type = str(event.get("type") or "").lower()
        if event_type in {
            "thread.started",
            "session.started",
            "turn.started",
            "turn.completed",
            "task.started",
            "task.completed",
            "exec.started",
            "exec.completed",
            "tool.started",
            "tool.completed",
            "tool_use",
            "function_call",
            "function_call_output",
        }:
            return ""
        message = event.get("message")
        if event_type == "error":
            text = extract_text_value(message)
            lower = text.lower()
            if "reconnecting" in lower or "request timed out" in lower:
                return ""
            return text
        candidates = [
            event.get("text"),
            event.get("content"),
            event.get("delta"),
            event.get("summary"),
            event.get("final_output"),
            event.get("output"),
        ]
        item = event.get("item")
        if isinstance(item, dict):
            candidates.extend([
                item.get("text"),
                item.get("content"),
                item.get("summary"),
            ])
        for candidate in candidates:
            text = extract_text_value(candidate)
            if text:
                return text
        return ""
