from __future__ import annotations

import json
import os
import time
from urllib.parse import urlparse

from .base import ProviderRunner
from .json_stream import JsonObjectStream, extract_text_value, is_internal_plain_line
from ..logging_utils import log_agent


class OpenCodeRunner(ProviderRunner):
    provider_name = "opencode"
    display_name = "OpenCode"
    log_prefix = "opencode"
    timeout_env_var = "OPENCODE_EXEC_TIMEOUT_SECONDS"
    default_timeout_seconds = 600

    @property
    def provider_dir(self) -> str:
        return f"{self.runtime._agent_dir}/.weagent/providers/opencode"

    @property
    def home_dir(self) -> str:
        return f"{self.provider_dir}/home"

    @property
    def resume_marker(self) -> str:
        return f"{self.provider_dir}/session_marker"

    def setup(self) -> None:
        os.makedirs(self.home_dir, exist_ok=True)
        self._write_noninteractive_config()
        self._stream_parser = JsonObjectStream()
        self._stderr_line_buffer = ""

    def build_command(self, message: str, retry_with_resume: bool = True) -> tuple[list[str], bool]:
        runtime = self.runtime
        full_message = f"{runtime._runtime_instruction()}\n\n用户任务：\n{message}"
        final_reply_rule = (
            "OpenCode final response rule:\n"
            "- weagent-report is only for progress/artifact cards; it is not the final chat reply.\n"
            "- Before finishing, call weagent-report with type=summary and a concise user-facing summary.\n"
            "- After all tool calls and reports, continue with a normal assistant text reply for the user.\n"
            "- The final assistant text must answer the user's request directly and must not be JSON or a weagent-report payload.\n"
            "- Do not end with placeholder text such as 'ready to reply', 'done', or 'task complete'.\n"
        )
        full_message = f"{full_message}\n\n{final_reply_rule}"
        use_continue = retry_with_resume and os.path.exists(self.resume_marker)
        cmd = [
            "opencode",
            "run",
            "--format",
            "json",
            "--dir",
            runtime._agent_dir,
            "--dangerously-skip-permissions",
        ]
        model_arg = self._model_arg()
        if model_arg:
            cmd.extend(["--model", model_arg])
        if use_continue:
            cmd.append("-c")
        cmd.append(full_message)
        return cmd, use_continue

    def environment(self) -> dict:
        runtime = self.runtime
        env = os.environ.copy()
        api_key = self._first_env(
            "OPENCODE_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        )
        base_url = self._opencode_base_url()
        model = self._first_env("OPENCODE_MODEL", "OPENAI_MODEL", "DEEPSEEK_MODEL", "ANTHROPIC_MODEL")
        env.update({
            "HOME": self.home_dir,
            "XDG_CONFIG_HOME": os.path.join(self.home_dir, ".config"),
            "XDG_DATA_HOME": os.path.join(self.home_dir, ".local", "share"),
            "XDG_CACHE_HOME": os.path.join(self.home_dir, ".cache"),
            "XDG_STATE_HOME": os.path.join(self.home_dir, ".local", "state"),
            "OPENCODE_HOME": self.home_dir,
            "WEAGENT_AGENT_ID": runtime.agent_id,
            "WEAGENT_WORKSPACE_NAME": runtime.workspace_name,
            "NO_COLOR": "1",
            "CI": "1",
        })
        if api_key:
            env["OPENCODE_API_KEY"] = api_key
            env["OPENAI_API_KEY"] = api_key
        if base_url:
            env["OPENCODE_BASE_URL"] = base_url
            env["OPENAI_BASE_URL"] = base_url
        if model:
            env["OPENCODE_MODEL"] = model
            env["OPENAI_MODEL"] = model
        return env

    def clean_output(self, stdout: str) -> str:
        return self._parse_output(stdout, final=True)

    def stream_chunk(self, chunk: str, stream_name: str) -> str:
        if stream_name != "stdout":
            return self._clean_stderr_stream_chunk(chunk)
        return self._parse_stream_chunk(chunk)

    def clean_error_output(self, stderr: str) -> str:
        return self._clean_migration_noise(stderr)

    def empty_output_message(self) -> str:
        return (
            "[Error] No final assistant reply from OpenCode. "
            "OpenCode only emitted tool/progress events; it must write the final answer as assistant text."
        )

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

    def fallback_output(self, stdout: str, stderr: str = "") -> str:
        reported = [
            text
            for text in self._reported_element_texts(stdout)
            if text and not self._is_placeholder_report(text)
        ]
        if reported:
            return reported[-1]
        return ""

    def should_retry_without_resume(self, stderr: str) -> bool:
        text = (stderr or "").lower()
        markers = (
            "no session",
            "session not found",
            "not found",
            "failed to continue",
            "unable to continue",
            "cannot continue",
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
                "opencode_session_marker_failed",
                level="warning",
                role=self.runtime.role,
                error=str(exc),
            )

    def is_auth_error(self, output: str) -> bool:
        text = (output or "").lower()
        return any(marker in text for marker in (
            "api key",
            "authentication",
            "not logged in",
            "provider credentials",
            "missing provider",
        ))

    def context_log_fields(self, used_resume: bool) -> dict:
        return {
            "use_continue": used_resume,
            "marker": self.resume_marker,
            "opencode_home": self.home_dir,
        }

    def started_payload(self) -> dict:
        payload = super().started_payload()
        payload["provider"] = self.provider_name
        return payload

    def _write_noninteractive_config(self) -> None:
        api_key = self._first_env(
            "OPENCODE_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        )
        base_url = self._opencode_base_url()
        model = self._model_name()
        provider = self._provider_name(base_url)
        if not (api_key and base_url and model):
            return

        config_dir = os.path.join(self.home_dir, ".config", "opencode")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "opencode.json")
        config = {
            "$schema": "https://opencode.ai/config.json",
            "model": f"{provider}/{model}",
            "small_model": f"{provider}/{model}",
            "provider": {
                provider: {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": provider,
                    "options": {
                        "baseURL": base_url,
                        "apiKey": "{env:OPENCODE_API_KEY}",
                    },
                    "models": {
                        model: {
                            "name": model,
                            "limit": {
                                "context": 128000,
                                "output": 32000,
                            },
                        },
                    },
                },
            },
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        log_agent(
            self.runtime.agent_id,
            "opencode_config_prepared",
            role=self.runtime.role,
            opencode_home=self.home_dir,
            config_path=config_path,
            provider_name=provider,
            model=model,
            base_url=base_url,
        )

    def _model_arg(self) -> str:
        explicit = self._first_env("OPENCODE_MODEL")
        if explicit and "/" in explicit:
            return explicit
        model = self._model_name()
        base_url = self._opencode_base_url()
        if model and base_url:
            return f"{self._provider_name(base_url)}/{model}"
        if explicit:
            return explicit
        return ""

    def _model_name(self) -> str:
        model = self._first_env("OPENCODE_MODEL", "OPENAI_MODEL", "DEEPSEEK_MODEL", "ANTHROPIC_MODEL")
        if "/" in model:
            return model.split("/", 1)[1]
        return model

    def _opencode_base_url(self) -> str:
        base_url = self._first_env("OPENCODE_BASE_URL", "OPENAI_BASE_URL")
        if base_url:
            return self._openai_compatible_base_url(base_url)
        deepseek_base = self._first_env("DEEPSEEK_BASE_URL")
        if deepseek_base:
            return self._openai_compatible_base_url(deepseek_base)
        anthropic_base = self._first_env("ANTHROPIC_BASE_URL")
        if anthropic_base:
            return self._openai_compatible_base_url(anthropic_base)
        return ""

    @classmethod
    def _openai_compatible_base_url(cls, base_url: str) -> str:
        cleaned = cls._clean_base_url(base_url)
        parsed = urlparse(cleaned)
        host = parsed.netloc.lower()
        if "deepseek" in host and cleaned.endswith("/anthropic"):
            return cleaned[:-len("/anthropic")] + "/v1"
        if "deepseek" in host and "/anthropic/" in cleaned:
            return cleaned.replace("/anthropic/", "/v1/", 1)
        return cleaned

    @staticmethod
    def _provider_name(base_url: str) -> str:
        host = urlparse(base_url or "").netloc.lower()
        if "deepseek" in host:
            return "deepseek"
        if "openai" in host:
            return "openai"
        return "openai_compatible"

    @staticmethod
    def _clean_base_url(value: str) -> str:
        text = str(value or "").strip().strip(" \t\r\n'\"").rstrip("/")
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid base URL: {text}")
        return text

    @staticmethod
    def _clean_migration_noise(value: str) -> str:
        if not value:
            return ""
        noise_markers = (
            "Performing one time database migration, may take a few minutes...",
            "sqlite-migration:done",
            "Database migration complete.",
        )
        kept_lines = []
        for line in str(value).splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if any(marker in cleaned for marker in noise_markers):
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines).strip()

    def _clean_stderr_stream_chunk(self, chunk: str) -> str:
        if not chunk:
            return ""
        text = getattr(self, "_stderr_line_buffer", "") + chunk
        complete_lines = []
        if text.endswith(("\n", "\r")):
            complete_lines = text.splitlines()
            self._stderr_line_buffer = ""
        else:
            lines = text.splitlines()
            if lines:
                complete_lines = lines[:-1]
                self._stderr_line_buffer = lines[-1]
            else:
                self._stderr_line_buffer = text
        return self._clean_migration_noise("\n".join(complete_lines))

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
    def _extract_text(event: dict, include_status: bool = False) -> str:
        if not isinstance(event, dict):
            return ""
        event_type = str(event.get("type") or "").lower()
        if event_type in {
            "tool_use",
            "tool_call",
            "tool_result",
            "tool.start",
            "tool.finish",
            "tool.started",
            "tool.completed",
            "tool_update",
            "step.start",
            "step.finish",
            "session.started",
            "session.updated",
        }:
            return ""
        part = event.get("part")
        if event_type == "part" and isinstance(part, dict):
            part_type = str(part.get("type") or "").lower()
            if part_type and part_type not in {"text", "message", "assistant_text"}:
                return ""
        message = event.get("message")
        if event_type == "error":
            text = extract_text_value(message) or OpenCodeRunner._extract_error_text(event)
            lower = text.lower()
            if "reconnecting" in lower or "request timed out" in lower:
                return ""
            return f"[Error] {text}" if text and not text.startswith("[Error]") else text
        candidates = [
            event.get("message"),
            event.get("text"),
            event.get("content"),
            event.get("delta"),
            event.get("summary"),
            event.get("output"),
            event.get("result"),
        ]
        for key in ("data", "item", "part", "message", "assistant", "response"):
            value = event.get(key)
            if isinstance(value, dict):
                candidates.extend([
                    value.get("text"),
                    value.get("content"),
                    value.get("delta"),
                    value.get("summary"),
                    value.get("output"),
                    value.get("result"),
                ])
        for candidate in candidates:
            text = extract_text_value(candidate)
            if text:
                return text
        return ""

    @staticmethod
    def _extract_error_text(event: dict) -> str:
        error = event.get("error")
        if not isinstance(error, dict):
            return ""
        data = error.get("data")
        parts = []
        name = extract_text_value(error.get("name"))
        if name:
            parts.append(name)
        if isinstance(data, dict):
            message = extract_text_value(data.get("message"))
            status_code = data.get("statusCode") or data.get("status")
            if message and status_code:
                parts.append(f"{message} ({status_code})")
            elif message:
                parts.append(message)
            metadata = data.get("metadata")
            if isinstance(metadata, dict) and metadata.get("url"):
                parts.append(str(metadata.get("url")))
        text = ": ".join(parts)
        return text.strip()

    @classmethod
    def _reported_element_texts(cls, stdout: str) -> list[str]:
        parser = JsonObjectStream()
        items = parser.feed_items(stdout or "", final=True)
        texts = []
        seen = set()
        for item_type, value in items:
            if item_type != "event" or not isinstance(value, dict):
                continue
            for text in cls._extract_report_texts_from_event(value):
                if text and text not in seen:
                    seen.add(text)
                    texts.append(text)
        return texts

    @classmethod
    def _extract_report_texts_from_event(cls, event: dict) -> list[str]:
        values = []
        part = event.get("part")
        if isinstance(part, dict):
            state = part.get("state")
            if isinstance(state, dict):
                values.extend([state.get("output"), state.get("text"), state.get("content")])
        item = event.get("item")
        if isinstance(item, dict):
            values.extend([item.get("aggregated_output"), item.get("output")])
        values.extend([event.get("output"), event.get("result")])

        texts = []
        for value in values:
            texts.extend(cls._extract_report_texts_from_value(value))
        return texts

    @classmethod
    def _extract_report_texts_from_value(cls, value) -> list[str]:
        if isinstance(value, dict):
            return cls._extract_report_texts_from_object(value)
        if not isinstance(value, str):
            return []
        texts = []
        for line in value.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            texts.extend(cls._extract_report_texts_from_object(payload))
        return texts

    @staticmethod
    def _extract_report_texts_from_object(payload: dict) -> list[str]:
        if not isinstance(payload, dict):
            return []
        element = payload.get("element")
        if not isinstance(element, dict):
            return []
        element_type = str(element.get("type") or "").lower()
        if element_type not in {"summary", "result", "text", "table", "file", "image", "code", "error"}:
            return []
        title = str(element.get("title") or "").strip()
        content = extract_text_value(element.get("content"))
        if title and content:
            return [f"{title}\n{content}"]
        if content:
            return [content]
        if title:
            return [title]
        return []

    @staticmethod
    def _is_placeholder_report(text: str) -> bool:
        compact = "".join(str(text or "").split()).lower()
        if not compact:
            return True
        placeholders = (
            "已准备回复用户",
            "准备回复用户",
            "已准备回复",
            "准备回复",
            "任务完成",
            "已完成",
            "完成",
            "done",
            "taskcomplete",
            "readytoreply",
            "readytorespond",
            "preparedreply",
        )
        if compact in placeholders:
            return True
        if compact.endswith("已准备回复用户") or compact.endswith("准备回复用户"):
            return True
        if compact.endswith("任务完成") and len(compact) <= 24:
            return True
        return False
