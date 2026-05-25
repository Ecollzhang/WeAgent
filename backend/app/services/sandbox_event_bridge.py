from datetime import datetime
import re

from app import db, socketio
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.agent_run_service import agent_run_service
from app.services.message_element_builder import (
    file_event_element,
    mentioned_file_elements,
    progress_element,
    text_delta_element,
)


class SandboxEventBridge:
    """Map sandbox runtime events into formal chat messages."""

    def handle_event(self, payload):
        session_id = payload.get('session_id')
        agent_id = payload.get('agent_id')
        event_type = payload.get('type')
        event_data = payload.get('data') or {}
        seq = payload.get('seq', 0)

        if not session_id or not agent_id:
            return

        conversation = Conversation.query.filter_by(
            sandbox_session_id=session_id
        ).first() or Conversation.query.get(session_id)
        if not conversation:
            return

        conversation.last_active_at = datetime.utcnow()

        run = agent_run_service.find_active_run(conversation.id, agent_id)
        if not run:
            db.session.commit()
            return

        message = Message.query.get(run.message_id) if run.message_id else None
        if not message:
            db.session.commit()
            return

        if event_type == 'agent_task_started':
            self._append_event(message, event_type, event_data, seq)
            element = progress_element(self._event_title(event_type, event_data), 'running',
                                       event_data)
            self._append_element(message, element)
            db.session.commit()
            self._emit_element(conversation.id, message, run, agent_id, element)
            self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type in ('claude_output_delta', 'claude_error_delta'):
            chunk = event_data.get('chunk', '')
            if chunk:
                message.raw_output = (message.raw_output or '') + chunk
                message.status = 'streaming'
                message.content = self._summary_text(message.raw_output)
                element = text_delta_element(chunk)
                self._append_element(message, element)
                run.last_seq = max(run.last_seq or 0, int(seq or 0))
                db.session.commit()
                self._emit_element(conversation.id, message, run, agent_id, element)
            return

        if event_type == 'file_write':
            element = file_event_element(session_id, event_data)
            self._append_event(message, event_type, event_data, seq)
            if element:
                key = element.get('data', {}).get('url') or element.get('data', {}).get('name')
                if self._append_element(message, element, unique_key=key):
                    db.session.commit()
                    self._emit_element(conversation.id, message, run, agent_id, element)
            else:
                db.session.commit()
                self._emit_step(conversation.id, message, run, agent_id, event_type, event_data, seq)
            return

        if event_type == 'agent_task_completed':
            self._append_event(message, event_type, event_data, seq)
            self._append_mentioned_files(message, run.sandbox_session_id or conversation.sandbox_session_id)
            self._append_element(message, progress_element(self._event_title(event_type, event_data),
                                                           'done', event_data))
            self._finish(message, run, conversation.id, agent_id, 'done', seq=seq)
            return

        if event_type == 'claude_stopped':
            self._append_event(message, event_type, event_data, seq)
            self._append_element(message, progress_element(self._event_title(event_type, event_data),
                                                           'stopped', event_data))
            self._finish(message, run, conversation.id, agent_id, 'stopped', seq=seq)
            return

        if event_type == 'error':
            error = event_data.get('error') or event_data.get('message') or 'Agent execution failed'
            self._append_event(message, event_type, event_data, seq)
            message.raw_output = ((message.raw_output or '') + f'\n{error}').strip()
            message.content = error
            self._append_element(message, progress_element(error, 'error', event_data))
            self._finish(message, run, conversation.id, agent_id, 'error',
                         error=error, seq=seq)

    def mark_agent_stopped(self, conversation_id, agent_id):
        run = agent_run_service.find_active_run(conversation_id, agent_id)
        if not run:
            return
        message = Message.query.get(run.message_id) if run.message_id else None
        conversation = Conversation.query.get(conversation_id)
        if message and conversation:
            self._finish(message, run, conversation_id, agent_id, 'stopped')

    def _finish(self, message, run, conversation_id, agent_id, status, error=None, seq=None):
        message.status = status
        if message.raw_output:
            message.content = self._summary_text(message.raw_output)
        elif status == 'stopped':
            message.content = '执行已停止'
            if not message.elements:
                self._append_element(message, progress_element('执行已停止', 'stopped'))
        run.status = status if status != 'done' else 'done'
        run.finished_at = datetime.utcnow()
        if error:
            run.error = error
        if seq is not None:
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
        db.session.commit()
        socketio.emit('conversation_message_status', {
            'conversation_id': conversation_id,
            'message_id': message.id,
            'run_id': run.id,
            'agent_id': agent_id,
            'status': status,
            'content': message.content,
            'elements': message.elements,
            'raw_output': message.raw_output,
            'sender_name': self._agent_name(Conversation.query.get(conversation_id), agent_id),
            'events': (message.meta or {}).get('events', []),
            'error': error,
        }, room=conversation_id)

    def _append_element(self, message, element, unique_key=None):
        elements = list(message.elements or [])
        if unique_key:
            exists = any(
                (item.get('data', {}).get('url') or item.get('data', {}).get('name')) == unique_key
                for item in elements
            )
            if exists:
                return False
        elements.append(element)
        message.elements = elements
        return True

    def _emit_element(self, conversation_id, message, run, agent_id, element):
        payload = {
            'conversation_id': conversation_id,
            'message_id': message.id,
            'run_id': run.id,
            'agent_id': agent_id,
            'sender_name': self._agent_name(Conversation.query.get(conversation_id), agent_id),
            'element': element,
            'raw_output': message.raw_output,
            'content': message.content,
            'status': message.status,
            'events': (message.meta or {}).get('events', []),
        }
        socketio.emit('conversation_message_element_stream', payload, room=conversation_id)

    def _append_mentioned_files(self, message, session_id):
        if not session_id:
            return
        text = '\n'.join(part for part in (message.raw_output, message.content) if part)
        for element in mentioned_file_elements(session_id, text):
            key = element.get('data', {}).get('url') or element.get('data', {}).get('name')
            self._append_element(message, element, unique_key=key)

    def _append_event(self, message, event_type, event_data, seq=None):
        meta = dict(message.meta or {})
        events = list(meta.get('events') or [])
        title = self._event_title(event_type, event_data)
        events.append({
            'type': event_type,
            'title': title,
            'data': event_data,
            'seq': seq,
            'created_at': datetime.utcnow().isoformat(),
        })
        meta['events'] = events[-100:]
        message.meta = meta

    def _emit_step(self, conversation_id, message, run, agent_id, event_type, event_data, seq):
        socketio.emit('conversation_message_step', {
            'conversation_id': conversation_id,
            'message_id': message.id,
            'run_id': run.id,
            'agent_id': agent_id,
            'sender_name': self._agent_name(Conversation.query.get(conversation_id), agent_id),
            'event': {
                'type': event_type,
                'title': self._event_title(event_type, event_data),
                'data': event_data,
                'seq': seq,
                'created_at': datetime.utcnow().isoformat(),
            },
            'events': (message.meta or {}).get('events', []),
        }, room=conversation_id)

    @staticmethod
    def _agent_name(conversation, agent_id):
        if not conversation:
            return agent_id
        participant = next(
            (p for p in conversation.participants
             if p.participant_type == 'agent' and p.participant_id == agent_id),
            None,
        )
        return participant.participant_name if participant else agent_id

    @staticmethod
    def _event_title(event_type, event_data):
        if event_type == 'agent_task_started':
            return event_data.get('message') or '开始执行任务'
        if event_type == 'file_write':
            return f"写入文件：{event_data.get('file', '')}"
        if event_type == 'agent_task_completed':
            return event_data.get('message') or '任务完成'
        if event_type == 'claude_stopped':
            return event_data.get('message') or '执行已停止'
        if event_type == 'error':
            return event_data.get('error') or '执行出错'
        return event_type

    @staticmethod
    def _summary_text(raw_output):
        text = (raw_output or '').strip()
        if not text:
            return '正在处理...'
        return text[-1200:]


sandbox_event_bridge = SandboxEventBridge()
