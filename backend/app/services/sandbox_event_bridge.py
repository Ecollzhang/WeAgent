import csv
import hashlib
import io
import json
import re
from datetime import timedelta

from flask import current_app
from sqlalchemy.orm.attributes import flag_modified

from app import db, socketio
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.agent_run_service import agent_run_service
from app.services.agent_output_sanitizer import public_agent_output
from app.services.message_element_builder import (
    file_event_element,
    mentioned_file_elements,
    progress_element,
    report_event_element,
    result_element,
)
from app.services.workspace_diff_service import workspace_diff_service
from app.utils.timezone import beijing_now, format_beijing


STARTED_EVENTS = {"provider_started", "claude_started"}
OUTPUT_DELTA_EVENTS = {"provider_output_delta", "claude_output_delta"}
ERROR_DELTA_EVENTS = {"provider_error_delta", "claude_error_delta"}
OUTPUT_EVENTS = {"provider_output", "claude_output"}
ERROR_OUTPUT_EVENTS = {"provider_error", "claude_error"}
STOPPED_EVENTS = {"provider_stopped", "claude_stopped"}
MAX_STORED_EVENTS = 100
LOW_VALUE_FILE_PARTS = {
    ".git",
    ".next",
    ".nuxt",
    ".output",
    ".parcel-cache",
    ".turbo",
    ".vite",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


class SandboxEventBridge:
    """Map sandbox runtime events into formal chat messages."""

    CARD_ROUTES = {
        ".csv": "table",
        ".py": "code", ".js": "code", ".jsx": "code", ".ts": "code", ".tsx": "code",
        ".css": "code", ".scss": "code", ".less": "code", ".md": "code", ".sql": "code",
        ".json": "code", ".xml": "code", ".yaml": "code", ".yml": "code", ".toml": "code",
        ".vue": "code", ".java": "code", ".c": "code", ".h": "code", ".cpp": "code",
        ".cc": "code", ".cxx": "code", ".hpp": "code", ".cs": "code", ".go": "code",
        ".rs": "code", ".php": "code", ".rb": "code", ".sh": "code", ".bat": "code",
        ".ps1": "code", ".kt": "code", ".swift": "code", ".dart": "code",
        ".html": "webpage", ".htm": "webpage",
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
        ".webp": "image", ".svg": "image", ".bmp": "image",
    }

    def handle_event(self, payload):
        session_id = payload.get("session_id")
        agent_id = payload.get("agent_id")
        event_type = payload.get("type")
        event_data = payload.get("data") or {}
        seq = payload.get("seq", 0)

        if not session_id or not agent_id:
            return

        conversation = Conversation.query.filter_by(
            sandbox_session_id=session_id
        ).first() or Conversation.query.get(session_id)
        if not conversation:
            return

        conversation.last_active_at = beijing_now()
        conversation.sandbox_expires_at = (
            beijing_now()
            + timedelta(
                seconds=max(
                    300,
                    int(current_app.config.get("SANDBOX_TTL_SECONDS", 72 * 3600)),
                )
            )
        )

        run = agent_run_service.find_active_run(conversation.id, agent_id)
        if not run:
            db.session.commit()
            return

        message = Message.query.get(run.message_id) if run.message_id else None
        if not message:
            db.session.commit()
            return

        if event_type == "file_write":
            print(
                f"[BridgeDebug] file_write received "
                f"session={session_id} agent={agent_id} "
                f"path={event_data.get('file') or event_data.get('path')} seq={seq}"
            )

        if event_type in STARTED_EVENTS:
            self._append_event(message, event_type, event_data, seq)
            element = progress_element(
                self._event_title(event_type, event_data), "running", event_data
            )
            self._append_element(message, element)
            message.status = "streaming"
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == "agent_task_started":
            self._append_event(message, event_type, event_data, seq)
            element = progress_element(
                self._event_title(event_type, event_data), "running", event_data
            )
            self._append_element(message, element)
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type in OUTPUT_DELTA_EVENTS | ERROR_DELTA_EVENTS:
            chunk = event_data.get("chunk", "")
            if chunk:
                message.raw_output = (message.raw_output or "") + chunk
                message.status = "streaming"
                message.content = self._summary_text(message.raw_output)
                run.last_seq = max(run.last_seq or 0, int(seq or 0))
                db.session.commit()
                self._emit_status(conversation.id, message, run, agent_id, "streaming")
            return

        if event_type in OUTPUT_EVENTS:
            output = event_data.get("output") or ""
            self._append_event(message, event_type, event_data, seq)
            if output and not message.raw_output:
                message.raw_output = output
                message.content = self._summary_text(message.raw_output)
            message.status = "streaming"
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
            db.session.commit()
            self._emit_status(conversation.id, message, run, agent_id, "streaming")
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type in ERROR_OUTPUT_EVENTS:
            output = event_data.get("output") or event_data.get("error") or ""
            self._append_event(message, event_type, event_data, seq)
            if output:
                element = progress_element(output, "error", event_data)
                self._append_element(message, element)
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
            db.session.commit()
            if output:
                self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == "agent_progress":
            self._append_event(message, event_type, event_data, seq)
            element = progress_element(
                self._event_title(event_type, event_data), "running", event_data
            )
            self._append_or_replace_progress(message, element, "agent_progress:heartbeat")
            message.status = "streaming"
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == "agent_report_element":
            element = report_event_element(session_id, event_data)
            if not element:
                element = progress_element("无效进度上报", "error", event_data)
            elif element.get("type") == "service":
                element = self._enrich_service_element(session_id, conversation, element)
            elif element.get("type") == "file":
                workflow_element = self._workflow_element_from_file(session_id, element)
                if workflow_element:
                    element = workflow_element
            self._append_event(message, event_type, event_data, seq)
            if element.get("type") == "summary":
                self._set_report_summary(message, element)
            else:
                self._attach_agent_metadata(element, conversation, session_id)
                self._append_element(message, element, unique_key=self._element_unique_key(element))
                self._enrich_file_element(
                    message, element, session_id, conversation.id, run, agent_id
                )
            message.status = "streaming"
            if element.get("type") == "summary" and not message.raw_output:
                message.content = element.get("content") or message.content
            elif element.get("type") in ("text", "result", "error"):
                message.content = element.get("content") or message.content
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == "file_write":
            if self._is_low_value_file_event(event_data):
                run.last_seq = max(run.last_seq or 0, int(seq or 0))
                db.session.commit()
                return
            element = file_event_element(session_id, event_data)
            if element:
                self._attach_agent_metadata(element, conversation, session_id)
                workflow_element = self._workflow_element_from_file(session_id, element)
                if workflow_element:
                    self._attach_agent_metadata(workflow_element, conversation, session_id)
                    element = workflow_element
            print(
                f"[BridgeDebug] file_write base element="
                f"{element.get('type') if element else None} "
                f"path={(element or {}).get('data', {}).get('path') if element else None}"
            )
            self._append_event(message, event_type, event_data, seq)
            progress = progress_element(
                self._event_title(event_type, event_data), "done", event_data
            )
            self._append_element(message, progress)
            diff_progress = progress_element("Building diff...", "running", event_data)
            self._append_or_replace_progress(message, diff_progress, "file_write:diff")
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, progress)
            self._emit_element(conversation.id, message, run, agent_id, diff_progress)

            diff_element = self._build_diff_element(session_id, event_data)
            print(
                f"[BridgeDebug] file_write diff_element="
                f"{diff_element.get('type') if diff_element else None}"
            )
            diff_done = progress_element(
                "Diff ready" if diff_element else "No diff generated", "done", event_data
            )
            self._append_or_replace_progress(message, diff_done, "file_write:diff")

            if element:
                key = element.get("data", {}).get("url") or element.get("data", {}).get("name")
                appended = self._append_element(message, element, unique_key=key)
                print(
                    f"[BridgeDebug] file_write appended_base={appended} "
                    f"elements_after_base={len(message.elements or [])}"
                )
                if diff_element:
                    self._append_element(message, diff_element)
                    print(
                        f"[BridgeDebug] file_write appended_diff "
                        f"elements_after_diff={len(message.elements or [])}"
                    )
                db.session.commit()
                self._emit_element(conversation.id, message, run, agent_id, diff_done)
                if diff_element:
                    self._emit_element(conversation.id, message, run, agent_id, diff_element)
                if appended:
                    self._emit_element(conversation.id, message, run, agent_id, element)
                    if element.get("type") == "file":
                        self._enrich_file_element(
                            message, element, session_id, conversation.id, run, agent_id
                        )
            else:
                db.session.commit()
                self._emit_element(conversation.id, message, run, agent_id, diff_done)
                if diff_element:
                    self._emit_element(conversation.id, message, run, agent_id, diff_element)
                self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == "agent_task_completed":
            self._append_event(message, event_type, event_data, seq)
            self._append_mentioned_files(
                message, run.sandbox_session_id or conversation.sandbox_session_id
            )
            summary = self._summary_text(message.raw_output)
            if summary and summary != "Processing...":
                self._append_element(message, result_element("Current output", summary, event_data))
            self._append_element(
                message,
                progress_element(self._event_title(event_type, event_data), "done", event_data),
            )
            self._finish(message, run, conversation.id, agent_id, "done", seq=seq)
            return

        if event_type in STOPPED_EVENTS:
            self._append_event(message, event_type, event_data, seq)
            element = progress_element(
                self._event_title(event_type, event_data), "stopped", event_data
            )
            self._append_or_replace_progress(message, element, "agent_progress:heartbeat")
            self._finish(message, run, conversation.id, agent_id, "stopped", seq=seq)
            return

        if event_type == "error":
            error = event_data.get("error") or event_data.get("message") or "Agent execution failed"
            self._append_event(message, event_type, event_data, seq)
            message.raw_output = ((message.raw_output or "") + f"\n{error}").strip()
            message.content = error
            self._append_element(message, progress_element(error, "error", event_data))
            self._finish(
                message, run, conversation.id, agent_id, "error", error=error, seq=seq
            )

    def mark_agent_stopped(self, conversation_id, agent_id):
        run = agent_run_service.find_active_run(conversation_id, agent_id)
        if not run:
            return
        message = Message.query.get(run.message_id) if run.message_id else None
        conversation = Conversation.query.get(conversation_id)
        if message and conversation:
            message.status = "stopped"
            if not (message.raw_output or message.content or message.elements):
                message.content = "Execution stopped"
                self._append_or_replace_progress(
                    message,
                    progress_element("Execution stopped", "stopped"),
                    "agent_progress:heartbeat",
                )
            db.session.commit()
            self._emit_status(conversation_id, message, run, agent_id, "stopped")

    def _finish(self, message, run, conversation_id, agent_id, status, error=None, seq=None):
        message.status = status
        if message.raw_output:
            message.content = self._summary_text(message.raw_output)
        elif self._report_summary(message):
            message.content = self._report_summary(message)
        elif status == "stopped" and not (message.content or message.elements):
            message.content = "Execution stopped"
            self._append_element(message, progress_element("Execution stopped", "stopped"))
        run.status = status if status != "done" else "done"
        run.finished_at = beijing_now()
        if error:
            run.error = error
        if seq is not None:
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
        db.session.commit()
        self._emit_status(conversation_id, message, run, agent_id, status, error=error)
        try:
            from app.services.conversation_service import conversation_service

            conversation = Conversation.query.get(conversation_id)
            if conversation and conversation.sandbox_status == "running":
                conversation_service.snapshot_sandbox(conversation)
        except Exception as exc:
            current_app.logger.warning(
                "sandbox snapshot after agent finish failed: %s",
                exc,
            )

    def _emit_status(self, conversation_id, message, run, agent_id, status, error=None):
        socketio.emit(
            "conversation_message_status",
            {
                "conversation_id": conversation_id,
                "message_id": message.id,
                "run_id": run.id,
                "agent_id": agent_id,
                "status": status,
                "content": message.content,
                "elements": message.elements,
                "raw_output": public_agent_output(message.raw_output),
                "sender_name": self._agent_name(Conversation.query.get(conversation_id), agent_id),
                "events": (message.meta or {}).get("events", []),
                "provider": self._message_provider(message),
                "error": error,
            },
            room=conversation_id,
        )

    def _append_element(self, message, element, unique_key=None):
        elements = list(message.elements or [])
        if unique_key:
            exists = any(
                self._element_unique_key(item) == unique_key
                for item in elements
            )
            if exists:
                return False
        elements.append(element)
        message.elements = elements
        return True

    def _append_or_replace_progress(self, message, element, progress_key):
        if not element:
            return False
        detail = dict(element.get("detail") or {})
        detail["progress_key"] = progress_key
        element["detail"] = detail
        data = dict(element.get("data") or {})
        data["progress_key"] = progress_key
        element["data"] = data

        elements = list(message.elements or [])
        for index, item in enumerate(elements):
            item_key = (
                (item.get("data") or {}).get("progress_key")
                or (item.get("detail") or {}).get("progress_key")
                or item.get("step_id")
            )
            if item.get("type") == "progress" and item_key == progress_key:
                elements[index] = element
                message.elements = elements
                flag_modified(message, "elements")
                return True
        elements.append(element)
        message.elements = elements
        flag_modified(message, "elements")
        return True

    def _set_report_summary(self, message, element):
        summary = (element.get("content") or "").strip()
        if not summary:
            return
        meta = dict(message.meta or {})
        meta["report_summary"] = summary
        message.meta = meta
        flag_modified(message, "meta")

    @staticmethod
    def _report_summary(message):
        meta = message.meta if isinstance(message.meta, dict) else {}
        return (meta.get("report_summary") or "").strip()

    def _emit_element(self, conversation_id, message, run, agent_id, element):
        payload = {
            "conversation_id": conversation_id,
            "message_id": message.id,
            "run_id": run.id,
            "agent_id": agent_id,
            "sender_name": self._agent_name(Conversation.query.get(conversation_id), agent_id),
            "element": element,
            "raw_output": public_agent_output(message.raw_output),
            "content": message.content,
            "status": message.status,
            "events": (message.meta or {}).get("events", []),
            "provider": self._message_provider(message),
        }
        socketio.emit("conversation_message_element_stream", payload, room=conversation_id)

    def _append_mentioned_files(self, message, session_id):
        if not session_id:
            return
        text = "\n".join(part for part in (message.raw_output, message.content) if part)
        for element in mentioned_file_elements(session_id, text):
            key = self._element_unique_key(element)
            self._append_element(message, element, unique_key=key)

    def _enrich_service_element(self, session_id, conversation, element):
        data = dict(element.get("data") or {})
        nested = data.get("service") if isinstance(data.get("service"), dict) else {}
        service_id = str(
            data.get("service_id")
            or data.get("id")
            or nested.get("service_id")
            or nested.get("id")
            or ""
        ).strip()
        if not session_id or not service_id:
            return element

        service = {}
        try:
            from app.sandbox import get_manager

            result = get_manager().get_service(
                session_id,
                service_id,
                user_id=getattr(conversation, "owner_id", None),
            )
            service = result.get("service") if isinstance(result, dict) else {}
        except Exception:
            service = {}

        merged = {**nested, **data}
        if isinstance(service, dict):
            merged.update(service)
        merged["service_id"] = service_id
        merged["id"] = merged.get("id") or service_id
        fallback_url = f"/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/"
        proxy_url = merged.get("proxy_url") or merged.get("url") or fallback_url
        merged["proxy_url"] = proxy_url
        merged["url"] = proxy_url
        if merged.get("name") and not element.get("content"):
            element["content"] = merged["name"]
        element["data"] = merged
        return element

    @staticmethod
    def _element_unique_key(element):
        if not isinstance(element, dict):
            return None
        data = element.get("data") or {}
        if element.get("type") == "service":
            nested = data.get("service") if isinstance(data.get("service"), dict) else {}
            service_id = data.get("service_id") or data.get("id") or nested.get("service_id") or nested.get("id")
            return f"service:{service_id}" if service_id else None
        return data.get("url") or data.get("name")

    def _append_event(self, message, event_type, event_data, seq=None):
        meta = dict(message.meta or {})
        events = list(meta.get("events") or [])
        provider = event_data.get("provider") if isinstance(event_data, dict) else None
        title = self._event_title(event_type, event_data)
        events.append(
            {
                "type": event_type,
                "title": title,
                "data": event_data,
                "provider": provider,
                "seq": seq,
                "created_at": format_beijing(beijing_now()),
            }
        )
        if provider:
            meta["provider"] = provider
        meta["events"] = self._compact_events(events)
        message.meta = meta
        flag_modified(message, "meta")

    @staticmethod
    def _compact_events(events):
        important = []
        tail = []
        seen_important = set()
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            seq = event.get("seq")
            if event_type in {
                "agent_task_started",
                "provider_started",
                "claude_started",
                "agent_report_element",
                "provider_output",
                "claude_output",
                "provider_error",
                "claude_error",
                "provider_stopped",
                "claude_stopped",
                "agent_task_completed",
                "error",
            }:
                key = (event_type, seq, event.get("title"))
                if key not in seen_important:
                    important.append(event)
                    seen_important.add(key)
            tail.append(event)

        merged = []
        seen = set()
        important_tail = important[-MAX_STORED_EVENTS:]
        for event in important_tail:
            key = (event.get("type"), event.get("seq"), event.get("created_at"))
            if key in seen:
                continue
            merged.append(event)
            seen.add(key)

        remaining = max(MAX_STORED_EVENTS - len(merged), 0)
        if remaining:
            extra = []
            for event in reversed(tail):
                key = (event.get("type"), event.get("seq"), event.get("created_at"))
                if key in seen:
                    continue
                extra.append(event)
                seen.add(key)
                if len(extra) >= remaining:
                    break
            merged.extend(reversed(extra))

        return sorted(
            merged[-MAX_STORED_EVENTS:],
            key=lambda event: (
                event.get("seq") if event.get("seq") is not None else 0,
                event.get("created_at") or "",
            ),
        )

    @staticmethod
    def _is_low_value_file_event(event_data):
        raw_path = ""
        if isinstance(event_data, dict):
            raw_path = event_data.get("file") or event_data.get("path") or ""
        path = str(raw_path).replace("\\", "/").strip("/")
        if path.startswith("workspace/"):
            path = path[len("workspace/"):]
        parts = {part for part in path.split("/") if part}
        return bool(parts & LOW_VALUE_FILE_PARTS)

    def _emit_step(self, conversation_id, message, run, agent_id, event_type, event_data, seq):
        socketio.emit(
            "conversation_message_step",
            {
                "conversation_id": conversation_id,
                "message_id": message.id,
                "run_id": run.id,
                "agent_id": agent_id,
                "sender_name": self._agent_name(Conversation.query.get(conversation_id), agent_id),
                "event": {
                    "type": event_type,
                    "title": self._event_title(event_type, event_data),
                    "data": event_data,
                    "provider": event_data.get("provider") if isinstance(event_data, dict) else None,
                    "seq": seq,
                    "created_at": format_beijing(beijing_now()),
                },
                "events": (message.meta or {}).get("events", []),
                "provider": self._message_provider(message),
            },
            room=conversation_id,
        )

    def _enrich_file_element(self, message, element, session_id,
                             conversation_id=None, run=None, agent_id=None):
        if element.get("type") != "file":
            return
        display_name = element.get("data", {}).get("name") or ""
        name = display_name.lower()
        print(f"[BridgeDebug] enrich start name={name}")
        ext = ""
        for candidate in self.CARD_ROUTES:
            if name.endswith(candidate):
                ext = candidate
                break
        if not ext:
            print(f"[BridgeDebug] enrich skip no_route name={name}")
            return
        path = element.get("data", {}).get("path")
        if not path:
            print(f"[BridgeDebug] enrich skip no_path name={name}")
            return
        workflow_card = self._workflow_element_from_file(session_id, element)
        if workflow_card:
            self._attach_agent_metadata(workflow_card, session_id=session_id, conversation_id=conversation_id)
            self._append_element(message, workflow_card, unique_key=self._element_unique_key(workflow_card))
            flag_modified(message, "elements")
            if conversation_id and run and agent_id:
                db.session.commit()
                self._emit_element(conversation_id, message, run, agent_id, workflow_card)
            return
        card_type = self.CARD_ROUTES[ext]
        for item in (message.elements or []):
            if item.get("type") == card_type and item.get("data", {}).get("path") == path:
                print(f"[BridgeDebug] enrich skip duplicate type={card_type} path={path}")
                return
        try:
            from app.sandbox import get_manager
            content_bytes, _ = get_manager().get_raw_file(session_id, path)
        except Exception:
            print(f"[BridgeDebug] enrich read_failed type={card_type} path={path}")
            return
        if not content_bytes:
            print(f"[BridgeDebug] enrich empty_content type={card_type} path={path}")
            return
        content = content_bytes.decode("utf-8", errors="replace")
        generator = {
            "table": self._gen_table,
            "code": self._gen_code,
            "webpage": self._gen_webpage,
            "image": self._gen_image,
        }.get(card_type)
        if not generator:
            print(f"[BridgeDebug] enrich skip no_generator type={card_type} path={path}")
            return
        card = generator(element, path, display_name or name, content)
        if not card:
            print(f"[BridgeDebug] enrich generator_returned_none type={card_type} path={path}")
            return
        self._attach_agent_metadata(card, session_id=session_id, conversation_id=conversation_id)
        self._append_element(message, card)
        flag_modified(message, "elements")
        print(
            f"[BridgeDebug] enrich appended type={card.get('type')} "
            f"path={path} elements_total={len(message.elements or [])}"
        )
        if conversation_id and run and agent_id:
            db.session.commit()
            self._emit_element(conversation_id, message, run, agent_id, card)

    def _attach_agent_metadata(self, element, conversation=None, session_id=None, conversation_id=None):
        if not element:
            return
        data = dict(element.get("data") or {})
        path = data.get("path") or ""
        workspace_name = data.get("workspace_name") or self._workspace_name_from_path(path)
        if not workspace_name:
            element["data"] = data
            return

        if conversation is None and conversation_id:
            conversation = Conversation.query.get(conversation_id)

        agent_id = ""
        agent_name = ""
        agent_avatar = ""
        agent_color = ""

        try:
            if session_id:
                from app.sandbox import get_manager
                session = get_manager().get_session(session_id)
                for cfg in (session.agents_config or []) if session else []:
                    cfg_workspace = cfg.get("workspace_name") or cfg.get("role") or cfg.get("agent_id")
                    if cfg_workspace == workspace_name:
                        agent_id = cfg.get("agent_id") or ""
                        agent_name = cfg.get("role") or cfg.get("name") or workspace_name
                        break
        except Exception:
            pass

        if conversation and (agent_id or workspace_name):
            for participant in conversation.participants or []:
                if participant.participant_type != "agent":
                    continue
                if agent_id and participant.participant_id == agent_id:
                    agent_name = participant.participant_name or agent_name
                    agent_avatar = participant.participant_avatar or ""
                    agent_color = participant.participant_color or ""
                    break
                if not agent_id and participant.participant_name == workspace_name:
                    agent_id = participant.participant_id
                    agent_name = participant.participant_name or workspace_name
                    agent_avatar = participant.participant_avatar or ""
                    agent_color = participant.participant_color or ""
                    break

        data["workspace_name"] = workspace_name
        if agent_id:
            data["agent_id"] = agent_id
        if agent_name:
            data["agent_name"] = agent_name
        if agent_avatar:
            data["agent_avatar"] = agent_avatar
        if agent_color:
            data["agent_color"] = agent_color
        element["data"] = data

    @staticmethod
    def _workspace_name_from_path(path):
        normalized = str(path or "").replace("\\", "/")
        if normalized.startswith("/workspace/"):
            normalized = normalized[len("/workspace/"):]
        parts = [part for part in normalized.split("/") if part]
        if len(parts) >= 3 and parts[0] == "agents":
            return parts[1]
        return ""

    def _gen_table(self, element, path, name, content):
        rows = list(csv.reader(io.StringIO(content)))
        if len(rows) < 2:
            return None
        headers = [cell.strip() for cell in rows[0]]
        body = [[cell.strip() for cell in row] for row in rows[1:]]
        if not headers or not body:
            return None
        return {
            "type": "table",
            "content": content[:200],
            "status": "done",
            "data": {
                "title": name.replace(".csv", ""),
                "headers": headers,
                "rows": body,
                "path": path,
            },
        }

    def _gen_code(self, element, path, name, content):
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        language_map = {
            "py": "python", "js": "javascript", "jsx": "javascript", "ts": "typescript",
            "tsx": "typescript", "css": "css", "scss": "scss", "less": "css",
            "md": "markdown", "sql": "sql", "json": "json", "xml": "xml",
            "yaml": "yaml", "yml": "yaml", "toml": "toml", "vue": "vue",
            "java": "java", "c": "c", "h": "c", "cpp": "cpp", "cc": "cpp",
            "cxx": "cpp", "hpp": "cpp", "cs": "csharp", "go": "go", "rs": "rust",
            "php": "php", "rb": "ruby", "sh": "shell", "bat": "shell",
            "ps1": "powershell", "kt": "kotlin", "swift": "swift", "dart": "dart",
        }
        return {
            "type": "code",
            "content": content,
            "status": "done",
            "data": {
                "title": name,
                "filename": name,
                "language": language_map.get(ext, ext or "text"),
                "path": path,
            },
        }

    def _workflow_element_from_file(self, session_id, element):
        data = dict(element.get("data") or {})
        name = str(data.get("name") or data.get("filename") or "").lower()
        path = str(data.get("path") or data.get("file") or "").replace("\\", "/")
        if not (name == "moderator-plan.json" or path.endswith("/moderator-plan.json")):
            return None
        try:
            from app.sandbox import get_manager
            content_bytes, _ = get_manager().get_raw_file(session_id, path)
            content = content_bytes.decode("utf-8", errors="replace")
            plan = json.loads(content)
        except Exception:
            return None
        return self._gen_workflow(plan, path)

    @staticmethod
    def _gen_workflow(plan, path):
        if not isinstance(plan, dict):
            return None
        tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
        team = plan.get("team") if isinstance(plan.get("team"), list) else []
        if tasks:
            nodes = []
            for index, task in enumerate(tasks):
                if not isinstance(task, dict):
                    continue
                task_id = str(task.get("id") or task.get("task_id") or f"task-{index + 1}")
                title = (
                    task.get("title")
                    or task.get("name")
                    or task.get("summary")
                    or task.get("description")
                    or f"任务 {index + 1}"
                )
                nodes.append({
                    "id": task_id,
                    "title": str(title),
                    "agent_id": task.get("agent_id") or task.get("assignee") or task.get("worker") or "",
                    "instruction": task.get("instruction") or task.get("description") or task.get("prompt") or "",
                    "x": 40 + (index % 3) * 280,
                    "y": 40 + (index // 3) * 180,
                })
        else:
            nodes = []
            for index, member in enumerate(team):
                if not isinstance(member, dict):
                    continue
                agent_id = str(member.get("agent_id") or f"agent-{index + 1}")
                if agent_id == "moderator":
                    continue
                nodes.append({
                    "id": agent_id,
                    "title": member.get("name") or agent_id,
                    "agent_id": agent_id,
                    "instruction": "根据主持人任务分配执行对应工作",
                    "x": 40 + (len(nodes) % 3) * 280,
                    "y": 40 + (len(nodes) // 3) * 180,
                })
        edges = []
        explicit_edges = plan.get("edges") if isinstance(plan.get("edges"), list) else []
        for edge in explicit_edges:
            if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
                edges.append({"from": str(edge.get("from")), "to": str(edge.get("to"))})
        if not edges and len(nodes) > 1:
            for index in range(len(nodes) - 1):
                edges.append({"from": nodes[index]["id"], "to": nodes[index + 1]["id"]})
        workflow = {
            "id": f"moderator-plan-{hashlib.md5((path or 'moderator-plan').encode('utf-8')).hexdigest()[:12]}",
            "name": "任务分配工作流",
            "summary": plan.get("summary") or "主持人生成的任务分配工作流",
            "nodes": nodes,
            "edges": edges,
            "parallel_groups": plan.get("parallel_groups") if isinstance(plan.get("parallel_groups"), list) else [],
            "source": "moderator-plan",
            "path": path,
            "raw_plan": plan,
        }
        return {
            "type": "workflow",
            "content": workflow["summary"],
            "status": "done",
            "data": workflow,
        }

    def _gen_webpage(self, element, path, name, content):
        return {
            "type": "webpage",
            "content": content[:200],
            "status": "done",
            "data": {
                "title": name,
                "filename": name,
                "language": "html",
                "path": path,
                "entry": True,
            },
        }

    def _gen_image(self, element, path, name, content):
        data = dict(element.get("data", {}) or {})
        data.setdefault("title", name)
        data["path"] = path
        return {
            "type": "image",
            "content": element.get("content") or name,
            "status": "done",
            "data": data,
        }

    @staticmethod
    def _build_diff_element(session_id, event_data):
        path = (event_data or {}).get("file") or (event_data or {}).get("path") or ""
        if not path:
            print("[BridgeDebug] diff skip empty_path")
            return None
        try:
            from app.sandbox import get_manager
            artifact = workspace_diff_service.capture_diff_after_write_event(
                get_manager(), session_id, path
            )
        except Exception:
            print(f"[BridgeDebug] diff exception path={path}")
            return None
        if not artifact or not artifact.diff_text:
            print(f"[BridgeDebug] diff none_or_empty path={path}")
            return None
        print(
            f"[BridgeDebug] diff built path={path} "
            f"additions={artifact.additions} deletions={artifact.deletions}"
        )
        return artifact.to_element()

    @staticmethod
    def _event_title(event_type, event_data):
        if event_type in STARTED_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} started"
        if event_type in OUTPUT_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} replied"
        if event_type in ERROR_OUTPUT_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} error output"
        if event_type == "agent_progress":
            message = event_data.get("message") or "Agent is running"
            elapsed = event_data.get("elapsed")
            if elapsed is not None:
                return f"{message} ({elapsed}s)"
            return message
        if event_type == "agent_report_element":
            return event_data.get("title") or event_data.get("content") or "Agent reported progress"
        if event_type == "agent_task_started":
            return event_data.get("message") or "Task started"
        if event_type == "file_write":
            return f"Wrote file: {event_data.get('file') or event_data.get('path') or ''}"
        if event_type == "agent_task_completed":
            return event_data.get("message") or "Task completed"
        if event_type in STOPPED_EVENTS:
            return event_data.get("message") or "Execution stopped"
        if event_type == "error":
            return event_data.get("error") or event_data.get("message") or "Execution failed"
        return event_type

    @staticmethod
    def _summary_text(raw_output):
        text = str(raw_output or "")
        text = re.sub(
            r"^##[ \t]+/?workspace/[^\r\n]+\r?\n"
            r"```[^\r\n]*\r?\n.*?^```[ \t]*(?:\r?\n|$)",
            "",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        text = re.sub(
            r"Reading additional input from stdin\.\.\.\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"<tool_call>.*?</tool_call>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return "Processing..."
        max_len = 12000
        if len(text) <= max_len:
            return text
        return text[-max_len:]

    @staticmethod
    def _provider_label(event_data):
        provider = ""
        if isinstance(event_data, dict):
            provider = (event_data.get("provider") or "").strip().lower()
            message = event_data.get("message") or ""
            if not provider and isinstance(message, str):
                lower = message.lower()
                if "claude" in lower:
                    provider = "claude"
                elif "codex" in lower:
                    provider = "codex"
                elif "opencode" in lower:
                    provider = "opencode"
        return {
            "claude": "Claude Code",
            "claude_code": "Claude Code",
            "codex": "Codex",
            "opencode": "OpenCode",
        }.get(provider, "Provider")

    @staticmethod
    def _message_provider(message):
        meta = message.meta if isinstance(message.meta, dict) else {}
        provider = meta.get("provider")
        if provider:
            return provider
        for event in reversed(meta.get("events") or []):
            if isinstance(event, dict):
                data = event.get("data") if isinstance(event.get("data"), dict) else {}
                provider = event.get("provider") or data.get("provider")
                if provider:
                    return provider
        return None

    @staticmethod
    def _agent_name(conversation, agent_id):
        if not conversation:
            return agent_id
        participant = next(
            (
                p for p in conversation.participants
                if p.participant_type == "agent" and p.participant_id == agent_id
            ),
            None,
        )
        return participant.participant_name if participant else agent_id


sandbox_event_bridge = SandboxEventBridge()
