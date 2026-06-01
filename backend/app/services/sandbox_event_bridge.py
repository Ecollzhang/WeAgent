from sqlalchemy.orm.attributes import flag_modified

from app import db, socketio
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.timezone import beijing_now, format_beijing
from app.utils.debug_logger import card_log
from app.services.agent_run_service import agent_run_service
from app.services.message_element_builder import (
    file_event_element,
    mentioned_file_elements,
    progress_element,
    report_event_element,
    result_element,
)
from app.services.workspace_diff_service import workspace_diff_service


STARTED_EVENTS = {"provider_started", "claude_started"}
OUTPUT_DELTA_EVENTS = {"provider_output_delta", "claude_output_delta"}
ERROR_DELTA_EVENTS = {"provider_error_delta", "claude_error_delta"}
OUTPUT_EVENTS = {"provider_output", "claude_output"}
ERROR_OUTPUT_EVENTS = {"provider_error", "claude_error"}
STOPPED_EVENTS = {"provider_stopped", "claude_stopped"}


class SandboxEventBridge:
    """Map sandbox runtime events into formal chat messages."""

    # Phase 2.5 unified card routes
    CARD_ROUTES = {
        '.csv': 'table',
        '.py': 'code', '.js': 'code', '.ts': 'code', '.tsx': 'code',
        '.css': 'code', '.scss': 'code', '.less': 'code',
        '.md': 'code', '.sql': 'code', '.json': 'code', '.xml': 'code',
        '.yaml': 'code', '.yml': 'code', '.toml': 'code', '.vue': 'code',
        '.java': 'code', '.c': 'code', '.h': 'code',
        '.cpp': 'code', '.cc': 'code', '.cxx': 'code', '.hpp': 'code',
        '.cs': 'code', '.go': 'code', '.rs': 'code',
        '.php': 'code', '.rb': 'code', '.sh': 'code', '.bat': 'code', '.ps1': 'code',
        '.kt': 'code', '.swift': 'code', '.dart': 'code',
        '.html': 'webpage', '.htm': 'webpage',
        '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
        '.gif': 'image', '.webp': 'image', '.svg': 'image', '.bmp': 'image',
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

        run = agent_run_service.find_active_run(conversation.id, agent_id)
        if not run:
            db.session.commit()
            return

        message = Message.query.get(run.message_id) if run.message_id else None
        if not message:
            db.session.commit()
            return

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
            self._append_event(message, event_type, event_data, seq)
            if element.get("type") == "summary":
                self._set_report_summary(message, element)
            else:
                self._append_element(message, element)
                self._enrich_file_element(message, element, session_id,
                                          conversation.id, run, agent_id)
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
            element = file_event_element(session_id, event_data)
            self._append_event(message, event_type, event_data, seq)
            progress = progress_element(
                self._event_title(event_type, event_data), "done", event_data
            )
            self._append_element(message, progress)
            diff_progress = progress_element("正在生成 diff...", "running", event_data)
            self._append_or_replace_progress(message, diff_progress, "file_write:diff")
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, progress)
            self._emit_element(conversation.id, message, run, agent_id, diff_progress)
            diff_element = self._build_diff_element(session_id, event_data)
            card_log("Card", f"[DEBUG P4] file_write event: path={(event_data or {}).get('file') or (event_data or {}).get('path')} has_file_element={bool(element)} has_diff_element={bool(diff_element)}")
            diff_done = progress_element("diff 已生成" if diff_element else "本次未生成 diff", "done", event_data)
            self._append_or_replace_progress(message, diff_done, "file_write:diff")
            if diff_element:
                self._append_element(message, diff_element)
                card_log("Card", f"[DEBUG P4] diff element appended: type={diff_element.get('type')} path={diff_element.get('data', {}).get('path')}")
            if element:
                key = element.get("data", {}).get("url") or element.get("data", {}).get("name")
                appended = self._append_element(message, element, unique_key=key)
                db.session.commit()
                card_log("Card", f"[DEBUG P4] message elements after file_write commit: count={len(message.elements or [])} types={[item.get('type') for item in (message.elements or [])]}")
                self._emit_element(conversation.id, message, run, agent_id, diff_done)
                if diff_element:
                    self._emit_element(conversation.id, message, run, agent_id, diff_element)
                if appended:
                    self._emit_element(conversation.id, message, run, agent_id, element)
                    self._enrich_file_element(message, element, session_id,
                                              conversation.id, run, agent_id)
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
            if summary and summary != "正在处理...":
                self._append_element(message, result_element("本轮输出结果", summary, event_data))
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
                message.content = "执行已停止"
                self._append_or_replace_progress(
                    message,
                    progress_element("执行已停止", "stopped"),
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
            message.content = "执行已停止"
            self._append_element(message, progress_element("执行已停止", "stopped"))
        run.status = status if status != "done" else "done"
        run.finished_at = beijing_now()
        if error:
            run.error = error
        if seq is not None:
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
        db.session.commit()
        self._emit_status(conversation_id, message, run, agent_id, status, error=error)

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
                "raw_output": message.raw_output,
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
                (item.get("data", {}).get("url") or item.get("data", {}).get("name"))
                == unique_key
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
            "raw_output": message.raw_output,
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
            key = element.get("data", {}).get("url") or element.get("data", {}).get("name")
            self._append_element(message, element, unique_key=key)

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
        meta["events"] = events[-100:]
        message.meta = meta
        flag_modified(message, "meta")

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

    # ====== Phase 2.5 card generators ======

    def _enrich_file_element(self, message, element, session_id,
                             conversation_id=None, run=None, agent_id=None):
        """Detect file extension and auto-generate content card, emit via socket."""
        if element.get("type") != "file":
            return
        name = (element.get("data", {}).get("name") or "").lower()
        ext = ""
        for c in self.CARD_ROUTES:
            if name.endswith(c):
                ext = c
                break
        if not ext:
            return
        path = element.get("data", {}).get("path")
        if not path:
            card_log("Card", f"{name}: path empty, skip")
            return
        ct = self.CARD_ROUTES[ext]
        card_log("Card", f"{name} -> type={ct} (ext={ext})")
        els = message.elements or []
        for e in els:
            if e.get("type") == ct and e.get("data", {}).get("path") == path:
                card_log("Card", f"{name}: duplicate {ct}, skip")
                return
        try:
            from app.sandbox import get_manager
            raw = get_manager().get_raw_file(session_id, path)
            if not raw or not raw[0]:
                card_log("Card", f"{name}: read empty")
                return
            content = raw[0].decode("utf-8", errors="replace")
            card_log("Card", f"{name}: read {len(raw[0])} bytes")
        except Exception as e:
            card_log("Card", f"{name}: read failed: {e}")
            return
        gen = {'table': self._gen_table, 'code': self._gen_code,
               'webpage': self._gen_webpage, 'image': self._gen_image}.get(ct)
        if not gen:
            return
        try:
            c = gen(element, path, name, content)
            if c:
                self._append_element(message, c)
                card_log("Card", f"{name}: generated {ct}")
                if conversation_id and run and agent_id:
                    self._emit_element(conversation_id, message, run, agent_id, c)
            elif ct == 'webpage':
                card_log("Card", f"{name}: webpage path, c=None, conv_id={conversation_id}, run={bool(run)}, agent_id={agent_id}")
        except Exception as e:
            card_log("Card", f"{name}: gen failed: {e}")

    def _gen_table(self, element, path, name, content):
        import csv, io
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if len(rows) < 2:
            card_log("Card", f"table: too few rows ({len(rows)})")
            return None
        h = [x.strip() for x in rows[0]]
        r = [[c.strip() for c in row] for row in rows[1:]]
        if not h or not r:
            card_log("Card", "table: empty headers/rows")
            return None
        card_log("Card", f"table: {len(h)} cols x {len(r)} rows")
        return {"type":"table","content":content[:200],"status":"done",
                "data":{"title":name.replace(".csv",""),"headers":h,"rows":r,"path":path}}

    def _gen_code(self, element, path, name, content):
        e = path.rsplit(".",1)[-1].lower() if "." in path else ""
        m = {'py':'python','js':'javascript','jsx':'javascript','ts':'typescript','tsx':'typescript',
             'css':'css','scss':'scss','less':'css','md':'markdown','sql':'sql',
             'json':'json','xml':'xml','yaml':'yaml','yml':'yaml','toml':'toml','vue':'vue',
             'java':'java','c':'c','h':'c','cpp':'cpp','cc':'cpp','cxx':'cpp','hpp':'cpp',
             'cs':'csharp','go':'go','rs':'rust','php':'php','rb':'ruby',
             'sh':'shell','bat':'shell','ps1':'powershell','kt':'kotlin','swift':'swift','dart':'dart'}
        return {"type":"code","content":content,"status":"done",
                "data":{"title":name,"filename":name,"language":m.get(e,e or 'text'),"path":path}}

    def _gen_webpage(self, element, path, name, content):
        """Mark original file element as webpage, no new element."""
        element.setdefault("data", {})
        element["data"]["subtype"] = "webpage"
        element["data"]["entry"] = True
        element["data"]["language"] = "html"
        element["data"]["filename"] = name
        return None

    def _gen_image(self, element, path, name, content):
        return None

    @staticmethod
    def _build_diff_element(session_id, event_data):
        path = (event_data or {}).get('file') or (event_data or {}).get('path') or ''
        if not path:
            card_log("Card", "[DEBUG P4] diff build skipped: empty path in file_write event")
            return None
        try:
            from app.sandbox import get_manager
            artifact = workspace_diff_service.capture_diff_after_write_event(
                get_manager(), session_id, path
            )
        except Exception as e:
            card_log("Card", f"diff build failed for {path}: {e}")
            return None
        if not artifact or not artifact.diff_text:
            card_log("Card", f"[DEBUG P4] diff build returned empty: path={path} artifact={bool(artifact)}")
            return None
        card_log("Card", f"diff built for {path}: +{artifact.additions} -{artifact.deletions}")
        return artifact.to_element()

    @staticmethod
    def _event_title(event_type, event_data):
        if event_type in STARTED_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} 已启动"
        if event_type in OUTPUT_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} 已回复"
        if event_type in ERROR_OUTPUT_EVENTS:
            return f"{SandboxEventBridge._provider_label(event_data)} 错误输出"
        if event_type == "agent_progress":
            message = event_data.get("message") or "Agent 正在执行"
            elapsed = event_data.get("elapsed")
            if elapsed is not None:
                return f"{message}（{elapsed}s）"
            return message
        if event_type == "agent_report_element":
            return event_data.get("title") or event_data.get("content") or "Agent 上报进度"
        if event_type == "agent_task_started":
            return event_data.get("message") or "开始执行任务"
        if event_type == "file_write":
            return f"写入文件：{event_data.get('file', '')}"
        if event_type == "agent_task_completed":
            return event_data.get("message") or "任务完成"
        if event_type in STOPPED_EVENTS:
            return event_data.get("message") or "执行已停止"
        if event_type == "error":
            return event_data.get("error") or event_data.get("message") or "执行出错"
        return event_type

    @staticmethod
    def _summary_text(raw_output):
        text = (raw_output or "").strip()
        if not text:
            return "正在处理..."
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


card_log("Card", "sandbox_event_bridge module loaded")

sandbox_event_bridge = SandboxEventBridge()
