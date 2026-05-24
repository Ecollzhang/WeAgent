import threading
import time
import random
import queue
import urllib.parse
from flask import current_app
from app.repositories.message_repo import message_repo
from app.repositories.conversation_repo import conversation_repo
from app.repositories.artifact_repo import artifact_repo
from app.models.message import Message

# ====== In-memory pub/sub for real-time SSE streaming ======
_queue_lock = threading.Lock()
_message_queues = {}  # conversation_id -> list of Queue


def subscribe(conversation_id):
    """Subscribe to real-time messages for a conversation. Returns a Queue."""
    q = queue.Queue()
    with _queue_lock:
        if conversation_id not in _message_queues:
            _message_queues[conversation_id] = []
        _message_queues[conversation_id].append(q)
    return q


def unsubscribe(conversation_id, q):
    """Unsubscribe from real-time messages."""
    with _queue_lock:
        if conversation_id in _message_queues:
            try:
                _message_queues[conversation_id].remove(q)
            except ValueError:
                pass


def broadcast(conversation_id, msg_dict):
    """Push a message dict to all subscribers of a conversation."""
    with _queue_lock:
        queues = list(_message_queues.get(conversation_id, []))
    for q in queues:
        try:
            q.put_nowait(msg_dict)
        except queue.Full:
            pass


def _message_dict(msg):
    """Convert Message model to dict with optional artifact enrichment."""
    data = msg.to_dict()
    if msg.artifact:
        data['artifact'] = {
            'id': msg.artifact.id,
            'artifact_type': msg.artifact.artifact_type,
            'title': msg.artifact.title,
            'language': msg.artifact.language,
        }
    return data


def _mock_agent_response(app, conversation_id, user_content):
    """Background thread: simulate agent thinking and posting responses.

    Messages are pushed to the in-memory queue for SSE subscribers
    to receive in real-time (no polling).
    """
    try:
        with app.app_context():
            from app import db

            conversation = conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return

            agent_participants = [p for p in conversation.participants
                                  if p.participant_type == 'agent']
            if not agent_participants:
                return

            for agent in agent_participants:
                agent_name = agent.participant_name or 'Agent'
                agent_id = agent.participant_id

                # 1) Thinking…
                time.sleep(0.5)
                msg = Message(
                    conversation_id=conversation_id,
                    sender_type='agent',
                    sender_id=agent_id,
                    content=f'🤔 **{agent_name}** 正在思考...',
                    message_type='text',
                    elements=[{'type': 'text', 'data': {'content': f'🤔 **{agent_name}** 正在思考...'}}],
                )
                db.session.add(msg)
                db.session.commit()
                broadcast(conversation_id, _message_dict(msg))

                # 2) Processing…
                time.sleep(0.8)
                msg = Message(
                    conversation_id=conversation_id,
                    sender_type='agent',
                    sender_id=agent_id,
                    content=f'⚙️ {agent_name} 正在分析你的请求...',
                    message_type='text',
                    elements=[{'type': 'text', 'data': {'content': f'⚙️ **{agent_name}** 正在分析你的请求...'}}],
                )
                db.session.add(msg)
                db.session.commit()
                broadcast(conversation_id, _message_dict(msg))

                # 3) Rich final reply — text, code, table, image, file, text
                time.sleep(1.2)

                # SVG bar chart (inline data URI — no external URL needed)
                svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="240">
  <rect fill="#f8f9fa" width="480" height="240" rx="8"/>
  <text fill="#1e293b" font-size="15" font-weight="bold" x="20" y="30">系统性能监控</text>
  <rect fill="#4080ff" x="40" y="80" width="55" height="90" rx="4"/>
  <rect fill="#667eea" x="120" y="100" width="55" height="70" rx="4"/>
  <rect fill="#764ba2" x="200" y="60" width="55" height="110" rx="4"/>
  <rect fill="#52c41a" x="280" y="90" width="55" height="80" rx="4"/>
  <rect fill="#faad14" x="360" y="110" width="55" height="60" rx="4"/>
  <text fill="#666" font-size="11" x="47" y="185">CPU</text>
  <text fill="#666" font-size="11" x="125" y="185">内存</text>
  <text fill="#666" font-size="11" x="207" y="185">磁盘</text>
  <text fill="#666" font-size="11" x="285" y="185">网络</text>
  <text fill="#666" font-size="11" x="367" y="185">延迟</text>
  <text fill="#4080ff" font-size="12" font-weight="bold" x="50" y="68">78%</text>
  <text fill="#667eea" font-size="12" font-weight="bold" x="130" y="88">62%</text>
  <text fill="#764ba2" font-size="12" font-weight="bold" x="210" y="48">91%</text>
  <text fill="#52c41a" font-size="12" font-weight="bold" x="290" y="78">73%</text>
  <text fill="#faad14" font-size="12" font-weight="bold" x="370" y="98">45%</text>
  <line stroke="#e8eaed" x1="20" y1="210" x2="460" y2="210"/>
  <text fill="#94a3b8" font-size="10" x="20" y="228">更新时间: 刚刚</text>
</svg>'''
                chart_data_uri = f'data:image/svg+xml,{urllib.parse.quote(svg)}'

                elements = [
                    {'type': 'text', 'data': {'content': f'你好！我是 **{agent_name}**，已收到你的消息。'}},
                    {'type': 'text', 'data': {'content': f'> {user_content}'}},
                    {'type': 'text', 'data': {'content': '以下是本次的处理结果：'}},
                    {'type': 'code', 'data': {
                        'language': 'python',
                        'content': (
                            'def analyze_performance(metrics):\n'
                            '    """分析系统性能指标"""\n'
                            '    results = {}\n'
                            '    for name, value in metrics.items():\n'
                            '        if value > 80:\n'
                            '            results[name] = "警告"\n'
                            '        elif value > 50:\n'
                            '            results[name] = "注意"\n'
                            '        else:\n'
                            '            results[name] = "正常"\n'
                            '    return results\n'
                            '\n'
                            '# 系统指标数据\n'
                            'system_metrics = {\n'
                            '    "CPU": 78,\n'
                            '    "内存": 62,\n'
                            '    "磁盘": 91,\n'
                            '    "网络": 73,\n'
                            '    "延迟": 45,\n'
                            '}\n'
                            'print(analyze_performance(system_metrics))'
                        ),
                        'filename': 'analyzer.py',
                    }},
                    {'type': 'table', 'data': {
                        'headers': ['指标', '当前值', '阈值', '状态', '建议'],
                        'rows': [
                            ['CPU 使用率', '78%', '80%', '⚠️ 注意', '检查异常进程'],
                            ['内存使用率', '62%', '85%', '✅ 正常', '-'],
                            ['磁盘 I/O', '91%', '90%', '🔴 警告', '需要扩容！'],
                            ['网络延迟', '45ms', '100ms', '✅ 正常', '-'],
                            ['错误率', '0.02%', '1%', '✅ 正常', '-'],
                        ],
                    }},
                    {'type': 'image', 'data': {
                        'url': chart_data_uri,
                        'alt': '系统性能监控图表',
                    }},
                    {'type': 'file', 'data': {
                        'name': 'performance_report_2024.html',
                        'url': '#',
                        'size': 245760,
                    }},
                    {'type': 'text', 'data': {'content': f'以上是 **{agent_name}** 的完整分析报告。磁盘 I/O 已达 91%，建议及时扩容。有其他问题请继续提问！'}},
                ]

                msg = Message(
                    conversation_id=conversation_id,
                    sender_type='agent',
                    sender_id=agent_id,
                    content=f'你好！我是 **{agent_name}**，已收到你的消息。\n\n> {user_content}\n\n这是一个模拟回复，后续将接入真实的 AI 模型。',
                    message_type='text',
                    elements=elements,
                )
                db.session.add(msg)
                db.session.commit()
                broadcast(conversation_id, _message_dict(msg))
    finally:
        # Signal SSE subscribers that this agent round is done
        broadcast(conversation_id, {'_type': 'agent_done'})


def _orchestrator_agent_response(app, conversation_id, user_message_id):
    """Background thread: route a persisted user message through orchestrator."""
    with app.app_context():
        from app.services.orchestrator_service import orchestrator_service

        orchestrator_service.dispatch_to_agents(conversation_id, user_message_id)


class MessageService:
    """Message business logic."""

    def send_message(self, conversation_id, sender_type, sender_id, content,
                     message_type='text', parent_message_id=None, artifact_id=None):
        """Send a message in a conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'

        message = message_repo.create(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            parent_message_id=parent_message_id,
            artifact_id=artifact_id
        )

        # Update conversation timestamp
        conversation_repo.update(conversation, updated_at=message.created_at)

        result = message.to_dict()
        if message.artifact:
            result['artifact'] = {
                'id': message.artifact.id,
                'artifact_type': message.artifact.artifact_type,
                'title': message.artifact.title,
                'language': message.artifact.language,
            }

        # If user sent the message, trigger real adapter-backed agent(s).
        if sender_type == 'user':
            has_agent = any(p.participant_type == 'agent'
                            for p in conversation.participants)
            if has_agent:
                app = current_app._get_current_object()
                thread = threading.Thread(
                    target=_orchestrator_agent_response,
                    args=(app, conversation_id, message.id),
                    daemon=True,
                )
                thread.start()

        return result, None

    def get_conversation_messages(self, conversation_id, page=1, per_page=50):
        """Get paginated messages for a conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'

        pagination = message_repo.get_conversation_messages(
            conversation_id, page=page, per_page=per_page
        )

        items = []
        for msg in pagination.items:
            msg_data = msg.to_dict()
            if msg.artifact:
                msg_data['artifact'] = {
                    'id': msg.artifact.id,
                    'artifact_type': msg.artifact.artifact_type,
                    'title': msg.artifact.title,
                    'language': msg.artifact.language,
                }
            items.append(msg_data)

        return {
            'items': items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        }, None

    def poll_messages(self, conversation_id, after=None):
        """Get messages newer than a reference message ID (by created_at)."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'

        query = Message.query.filter_by(conversation_id=conversation_id)

        if after:
            ref = Message.query.get(after)
            if ref:
                query = query.filter(Message.created_at > ref.created_at)

        messages = query.order_by(Message.created_at.asc()).all()
        items = []
        for msg in messages:
            msg_data = msg.to_dict()
            if msg.artifact:
                msg_data['artifact'] = {
                    'id': msg.artifact.id,
                    'artifact_type': msg.artifact.artifact_type,
                    'title': msg.artifact.title,
                    'language': msg.artifact.language,
                }
            items.append(msg_data)

        return {'items': items}, None

    def toggle_pin(self, message_id):
        """Toggle pin status of a message."""
        message = message_repo.toggle_pin(message_id)
        if not message:
            return None, 'Message not found'
        return {'id': message.id, 'is_pinned': message.is_pinned}, None

    def get_pinned_messages(self, conversation_id):
        """Get pinned messages for a conversation."""
        messages = message_repo.get_pinned_messages(conversation_id)
        return [msg.to_dict() for msg in messages], None


message_service = MessageService()
