import threading
import queue
import uuid
import json
import re
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified
from app import db, socketio
from app.repositories.message_repo import message_repo
from app.repositories.conversation_repo import conversation_repo
from app.repositories.artifact_repo import artifact_repo
from app.models.agent import Agent
from app.models.message import Message
from app.services.agent_run_service import agent_run_service
from app.utils.timezone import beijing_now
from app.services.message_element_builder import (
    file_event_element,
    mentioned_file_elements,
    report_event_element,
)

MODERATOR_AGENT_ID = 'moderator'

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
    _ensure_structured_elements(msg)
    data = msg.to_dict()
    if msg.sender_type == 'agent':
        conversation = conversation_repo.get_by_id(msg.conversation_id)
        if conversation:
            participant = next(
                (p for p in conversation.participants
                 if p.participant_type == 'agent' and p.participant_id == msg.sender_id),
                None,
            )
            if participant:
                data['sender_name'] = participant.participant_name or msg.sender_id
                data['sender_avatar'] = participant.participant_avatar or ''
                data['sender_color'] = participant.participant_color or ''
    if msg.artifact:
        data['artifact'] = {
            'id': msg.artifact.id,
            'artifact_type': msg.artifact.artifact_type,
            'title': msg.artifact.title,
            'language': msg.artifact.language,
        }
    return data


def _ensure_structured_elements(msg):
    """Backfill persisted structured elements from saved events/raw output."""
    if not msg or msg.sender_type != 'agent':
        return

    raw = (msg.raw_output or '').strip()
    events = []
    if isinstance(msg.meta, dict):
        events = msg.meta.get('events') or []
    if not raw and not events:
        return

    conversation = conversation_repo.get_by_id(msg.conversation_id)
    session_id = None
    if conversation:
        session_id = conversation.sandbox_session_id or conversation.id
    session_id = session_id or msg.conversation_id

    elements = list(msg.elements or [])
    changed = False

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get('type')
        event_data = event.get('data') or {}
        element = None
        if event_type == 'agent_report_element':
            element = report_event_element(session_id, event_data)
        elif event_type == 'file_write':
            if _is_internal_file_event(event_data):
                continue
            element = file_event_element(session_id, event_data)
        if _append_element_once(elements, element):
            changed = True

    has_result = any(el.get('type') in ('result', 'error') for el in elements if isinstance(el, dict))
    has_table = any(el.get('type') == 'table' for el in elements if isinstance(el, dict))
    has_file = any(el.get('type') in ('file', 'image') for el in elements if isinstance(el, dict))
    if not raw:
        if changed:
            msg.elements = elements
            flag_modified(msg, 'elements')
            db.session.add(msg)
            db.session.commit()
        return

    tables, text_without_tables = _extract_markdown_tables(raw)
    if tables and not has_table:
        for index, table in enumerate(tables, start=1):
            elements.append({
                'type': 'table',
                'content': table.get('title') or f'表格 {index}',
                'status': 'done',
                'data': {
                    'title': table.get('title') or f'表格 {index}',
                    'headers': table['headers'],
                    'rows': table['rows'],
                },
            })
        changed = True

    result_text = (text_without_tables or raw).strip()
    if result_text and not has_result:
        elements.append({
            'type': 'result',
            'content': result_text,
            'status': 'done',
            'data': {
                'title': '输出结果',
                'content': result_text,
            },
        })
        if not msg.content or msg.content == '正在处理...':
            msg.content = result_text[-12000:]
        changed = True

    if not has_file:
        conversation = conversation_repo.get_by_id(msg.conversation_id)
        session_id = conversation.sandbox_session_id if conversation else None
        for element in mentioned_file_elements(session_id, raw):
            key = element.get('data', {}).get('url') or element.get('data', {}).get('path') or element.get('data', {}).get('name')
            exists = any(
                (item.get('data', {}).get('url') or item.get('data', {}).get('path') or item.get('data', {}).get('name')) == key
                for item in elements if isinstance(item, dict)
            )
            if not exists:
                elements.append(element)
                changed = True

    if changed:
        msg.elements = elements
        flag_modified(msg, 'elements')
        db.session.add(msg)
        db.session.commit()


def _append_element_once(elements, element):
    if not isinstance(element, dict):
        return False
    key = _element_key(element)
    if key and any(_element_key(item) == key for item in elements if isinstance(item, dict)):
        return False
    elements.append(element)
    return True


def _element_key(element):
    if not isinstance(element, dict):
        return ''
    data = element.get('data') if isinstance(element.get('data'), dict) else {}
    element_type = element.get('type') or ''
    for field in ('url', 'path', 'name', 'step_id', 'title'):
        value = data.get(field) or element.get(field)
        if value:
            return f'{element_type}:{value}'
    content = element.get('content')
    if content:
        return f'{element_type}:{content}'
    return ''


def _is_internal_file_event(event_data):
    path = str((event_data or {}).get('file') or '')
    name = path.replace('\\', '/').rsplit('/', 1)[-1]
    return name.startswith('.weagent_')


def _extract_markdown_tables(text):
    lines = str(text or '').replace('\r\n', '\n').split('\n')
    tables = []
    kept = []
    i = 0
    while i < len(lines):
        line = lines[i]
        next_index = _next_non_empty_line_index(lines, i + 1)
        next_line = lines[next_index] if next_index != -1 else ''
        if _is_markdown_table_row(line) and _is_markdown_table_separator(next_line):
            headers = _parse_markdown_table_row(line)
            rows = []
            i = next_index + 1
            while i < len(lines):
                if not lines[i].strip():
                    i += 1
                    continue
                if not _is_markdown_table_row(lines[i]):
                    break
                rows.append(_parse_markdown_table_row(lines[i]))
                i += 1
            if headers and rows:
                tables.append({'headers': headers, 'rows': rows})
            continue
        kept.append(line)
        i += 1
    return tables, '\n'.join(kept).strip()


def _next_non_empty_line_index(lines, start):
    for index in range(start, len(lines)):
        if str(lines[index] or '').strip():
            return index
    return -1


def _is_markdown_table_row(line):
    text = str(line or '').strip()
    if not text or '|' not in text:
        return False
    return len(_parse_markdown_table_row(text)) >= 2


def _is_markdown_table_separator(line):
    if not _is_markdown_table_row(line):
        return False
    cells = _parse_markdown_table_row(line)
    return len(cells) >= 2 and all(re.match(r'^:?-{2,}:?$', re.sub(r'\s+', '', cell)) for cell in cells)


def _parse_markdown_table_row(line):
    text = str(line or '').strip()
    if text.startswith('|'):
        text = text[1:]
    if text.endswith('|'):
        text = text[:-1]
    return [cell.strip() for cell in text.split('|')]



class MessageService:
    """Message business logic."""

    def send_message(self, conversation_id, sender_type, sender_id, content,
                     message_type='text', parent_message_id=None, artifact_id=None,
                     target_agent_ids=None, agent_configs=None, workflow=None):
        """Send a message in a conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'

        agent_participants = [p for p in conversation.participants if p.participant_type == 'agent']
        target_agent_ids = self._normalize_target_agent_ids(target_agent_ids)
        if sender_type == 'user' and not target_agent_ids:
            target_agent_ids = self._parse_mentioned_agent_ids(content, agent_participants)
        target_participants = self._target_participants_from_ids(
            conversation,
            agent_participants,
            target_agent_ids,
        )
        if sender_type == 'user' and target_agent_ids and len(target_participants) != len(target_agent_ids):
            return None, '指定的 Agent 不在当前会话中'
        if sender_type == 'user' and target_participants:
            disabled_ids = self._disabled_session_agent_ids(agent_configs)
            disabled_targets = [
                p.participant_name or p.participant_id
                for p in target_participants
                if str(p.participant_id) in disabled_ids
            ]
            if disabled_targets:
                return None, '以下 Agent 已在当前会话中禁用，请先在智能体配置中启用后再 @：' + '、'.join(disabled_targets)
        message_meta = {}
        if sender_type == 'user' and target_participants:
            message_meta.update({
                'dispatch_mode': 'direct',
                'mentions': [
                    {
                        'agent_id': p.participant_id,
                        'name': p.participant_name or p.participant_id,
                    }
                    for p in target_participants
                ],
            })
        if sender_type == 'user':
            workflow_meta = self._selected_workflow_meta(workflow)
            if workflow_meta:
                message_meta['selected_workflow'] = workflow_meta
        if not message_meta:
            message_meta = None

        message = message_repo.create(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            parent_message_id=parent_message_id,
            artifact_id=artifact_id,
            meta=message_meta,
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

        # If user sent the message, dispatch agents through the sandbox runtime
        if sender_type == 'user':
            has_agent = any(p.participant_type == 'agent'
                            for p in conversation.participants)
            if has_agent:
                app = current_app._get_current_object()
                thread = threading.Thread(
                    target=self._dispatch_agent_sandbox,
                    args=(app, conversation_id, content, message.id, target_agent_ids, agent_configs, workflow),
                    daemon=True,
                )
                thread.start()

        return result, None

    def _dispatch_single_agent_sandbox(self, app, conversation_id, user_content,
                                       user_message_id=None):
        self._dispatch_agent_sandbox(app, conversation_id, user_content, user_message_id)

    def _dispatch_agent_sandbox(self, app, conversation_id, user_content,
                                user_message_id=None, target_agent_ids=None, agent_configs=None, workflow=None):
        """Dispatch a user round to one agent or a backend-orchestrated group."""
        with app.app_context():
            conversation = conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return

            agent_participants = [
                p for p in conversation.participants
                if p.participant_type == 'agent'
            ]
            if not agent_participants:
                return
            from app.services.conversation_service import conversation_service
            _, runtime_error = conversation_service.ensure_sandbox_runtime(
                conversation,
                user_id=conversation.owner_id,
            )
            if runtime_error:
                self._emit_system_error(
                    conversation.id,
                    f'沙箱恢复失败，聊天和既有产物仍已保留：{runtime_error}',
                )
                return
            user_content = self._apply_session_agent_configs(
                user_content,
                agent_configs,
                agent_participants,
            )
            user_content = self._apply_selected_workflow(user_content, workflow)
            direct_targets = self._resolve_direct_target_participants(
                conversation,
                agent_participants,
                user_content,
                target_agent_ids,
            )
            if direct_targets:
                self._dispatch_direct_agent_round(
                    conversation,
                    direct_targets,
                    user_content,
                    user_message_id,
                )
                return
            if len(agent_participants) == 1:
                self._dispatch_single_agent_round(conversation, agent_participants[0],
                                                  user_content, user_message_id)
            else:
                self._dispatch_multi_agent_round(conversation, agent_participants,
                                                 user_content, user_message_id, agent_configs)

    @staticmethod
    def _apply_session_agent_configs(user_content, agent_configs, agent_participants):
        config_map = MessageService._normalize_session_agent_configs(agent_configs)
        if not config_map:
            return user_content

        blocks = []
        for participant in agent_participants:
            cfg = config_map.get(str(participant.participant_id))
            if not cfg:
                continue
            lines = [f"Agent: {cfg.get('role') or participant.participant_name or participant.participant_id}"]
            lines.append(f"Agent ID: {participant.participant_id}")
            if cfg.get('enabled') is False:
                lines.append("状态: 当前会话中已禁用。不要把任务分配给它；如果用户任务必须依赖该 Agent，先回复用户说明需要启用后才能继续。")
            if cfg.get('system_prompt'):
                lines.append(f"会话级系统提示词: {cfg.get('system_prompt')}")
            if cfg.get('skill'):
                lines.append(f"会话级技能/工作方式: {cfg.get('skill')}")
            lines.append("SESSION_AGENT_CONFIG_JSON: " + json.dumps({
                'agent_id': participant.participant_id,
                'role': cfg.get('role') or participant.participant_name or participant.participant_id,
                'system_prompt': cfg.get('system_prompt') or '',
                'skill': cfg.get('skill') or '',
                'enabled': cfg.get('enabled', True),
                'adapter_name': cfg.get('adapter_name') or '',
            }, ensure_ascii=False))
            if len(lines) > 1:
                blocks.append("\n".join(lines))

        if not blocks:
            return user_content
        config_text = "\n\n".join(blocks)
        return (
            f"{user_content}\n\n"
            "【当前会话级 Agent 配置覆盖】\n"
            "以下配置只对当前会话调度生效，不代表全局 Agent 配置变更。\n"
            "SESSION_AGENT_CONFIG_CONTEXT:\n"
            f"{config_text}"
        )

    @staticmethod
    def _normalize_session_agent_configs(agent_configs):
        if isinstance(agent_configs, list):
            return {
                str(item.get('agent_id')): item
                for item in agent_configs
                if isinstance(item, dict) and item.get('agent_id')
            }
        if isinstance(agent_configs, dict):
            return {
                str(key): value
                for key, value in agent_configs.items()
                if isinstance(value, dict)
            }
        return {}

    @staticmethod
    def _disabled_session_agent_ids(agent_configs):
        return {
            str(agent_id)
            for agent_id, cfg in MessageService._normalize_session_agent_configs(agent_configs).items()
            if cfg.get('enabled') is False
        }

    @staticmethod
    def _apply_selected_workflow(user_content, workflow):
        if not isinstance(workflow, dict) or not workflow:
            return user_content
        workflow_context = MessageService._selected_workflow_meta(workflow)
        if not workflow_context:
            return user_content
        return (
            f"{user_content}\n\n"
            "【用户选择的工作流图】\n"
            "主持 Agent 必须优先按照该工作流图进行任务分配；如果工作流与用户任务冲突，先说明需要用户调整工作流。\n"
            "SELECTED_WORKFLOW_JSON: "
            + json.dumps(workflow_context, ensure_ascii=False)
        )

    @staticmethod
    def _selected_workflow_meta(workflow):
        if not isinstance(workflow, dict) or not workflow:
            return None
        return {
            'id': workflow.get('id') or '',
            'name': workflow.get('name') or '未命名工作流',
            'nodes': workflow.get('nodes') if isinstance(workflow.get('nodes'), list) else [],
            'edges': workflow.get('edges') if isinstance(workflow.get('edges'), list) else [],
            'parallel_groups': workflow.get('parallel_groups') if isinstance(workflow.get('parallel_groups'), list) else [],
        }

    @staticmethod
    def _normalize_target_agent_ids(target_agent_ids):
        if not isinstance(target_agent_ids, list):
            return []
        result = []
        seen = set()
        for item in target_agent_ids:
            agent_id = str(item or '').strip()
            if not agent_id or agent_id in seen:
                continue
            seen.add(agent_id)
            result.append(agent_id)
        return result

    def _target_participants_from_ids(self, conversation, agent_participants, target_agent_ids):
        ids = set(self._normalize_target_agent_ids(target_agent_ids))
        if not ids:
            return []
        return [
            p for p in agent_participants
            if p.participant_id in ids
        ]

    def _resolve_direct_target_participants(self, conversation, agent_participants,
                                            user_content, target_agent_ids=None):
        explicit = self._target_participants_from_ids(
            conversation,
            agent_participants,
            target_agent_ids,
        )
        if explicit:
            return explicit
        mentioned_ids = self._parse_mentioned_agent_ids(user_content, agent_participants)
        return self._target_participants_from_ids(conversation, agent_participants, mentioned_ids)

    @staticmethod
    def _parse_mentioned_agent_ids(content, agent_participants):
        text = str(content or '')
        if '@' not in text:
            return []
        matches = re.findall(r'@([^\s@，,：:；;]+)', text)
        if not matches:
            return []
        by_name = {}
        for p in agent_participants:
            names = {
                p.participant_id,
                p.participant_name or '',
            }
            for name in names:
                clean = str(name or '').strip()
                if clean:
                    by_name[clean] = p.participant_id
        result = []
        seen = set()
        for raw in matches:
            agent_id = by_name.get(str(raw or '').strip())
            if agent_id and agent_id not in seen:
                seen.add(agent_id)
                result.append(agent_id)
        return result

    @staticmethod
    def _strip_direct_mentions(content, participants):
        text = str(content or '')
        for p in participants:
            for name in (p.participant_name, p.participant_id):
                clean = str(name or '').strip()
                if clean:
                    text = re.sub(rf'@{re.escape(clean)}(?=\s|$|，|,|：|:|；|;)', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _dispatch_direct_agent_round(self, conversation, participants, user_content,
                                     user_message_id=None):
        if not conversation.sandbox_session_id:
            self._emit_system_error(conversation.id, '该会话没有可用的沙箱容器。')
            return

        round_id = str(uuid.uuid4())
        threads = []
        app = current_app._get_current_object()
        for participant in participants:
            thread = threading.Thread(
                target=self._run_direct_agent_task,
                args=(app, conversation.id, round_id, user_message_id, user_content, participant.participant_id),
                daemon=True,
            )
            threads.append(thread)
            thread.start()

    def _run_direct_agent_task(self, app, conversation_id, round_id, user_message_id,
                               user_content, participant_id):
        with app.app_context():
            conversation = conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return
            participant = self._get_conversation_participant(conversation_id, participant_id)
            if not participant:
                self._emit_system_error(conversation_id, f'指定 Agent 不在当前会话中：{participant_id}')
                return
            clean_task = self._strip_direct_mentions(user_content, [participant])
            prompt = (
                '用户在群聊中明确 @ 你处理本消息，请你直接回答或完成任务，'
                '不要等待主持 Agent 分派。\n\n'
                f'用户原始消息：\n{user_content}\n\n'
                f'去除 @ 后的任务：\n{clean_task or user_content}\n'
            )
            agent_msg, run = self._create_agent_message_and_run(
                conversation,
                participant,
                round_id,
                user_message_id,
                f'{participant.participant_name or participant.participant_id} 正在处理 @ 指定任务...',
            )
            try:
                from app.sandbox import get_manager
                result = get_manager().send_message(
                    conversation.sandbox_session_id,
                    participant.participant_id,
                    prompt,
                )
                if result.get('status') == 'error':
                    result = self._retry_agent_after_model_error(
                        conversation, participant.participant_id, prompt, result
                    )
                if result.get('status') == 'error':
                    self._mark_agent_message_failed(
                        agent_msg.id,
                        run.id,
                        result.get('error', 'Agent execution failed'),
                    )
                    return
                self._mark_agent_message_done_if_active(
                    agent_msg.id,
                    run.id,
                    participant.participant_id,
                    result.get('reply', ''),
                )
            except Exception as e:
                self._mark_agent_message_failed(agent_msg.id, run.id, str(e))

    def _dispatch_single_agent_round(self, conversation, participant, user_content,
                                     user_message_id=None):
        """Create one agent message and run the sandbox call in background."""
        if not conversation.sandbox_session_id:
            self._emit_system_error(conversation.id, '该会话没有可用的沙箱容器。')
            return

        round_id = str(uuid.uuid4())
        agent_msg, run = self._create_agent_message_and_run(
            conversation, participant, round_id, user_message_id, '正在处理...'
        )

        try:
            from app.sandbox import get_manager
            result = get_manager().send_message(
                conversation.sandbox_session_id,
                participant.participant_id,
                user_content,
            )
            if result.get('status') == 'error':
                result = self._retry_agent_after_model_error(
                    conversation, participant.participant_id, user_content, result
                )
                if result.get('status') == 'error':
                    self._mark_agent_message_failed(agent_msg.id, run.id,
                                                    result.get('error', 'Agent execution failed'))
                    return
                self._mark_agent_message_done_if_active(
                    agent_msg.id,
                    run.id,
                    participant.participant_id,
                    result.get('reply', ''),
                )
            else:
                self._mark_agent_message_done_if_active(
                    agent_msg.id,
                    run.id,
                    participant.participant_id,
                    result.get('reply', ''),
                )
        except Exception as e:
            self._mark_agent_message_failed(agent_msg.id, run.id, str(e))

    def _dispatch_multi_agent_round(self, conversation, agent_participants,
                                    user_content, user_message_id=None, agent_configs=None):
        if not conversation.sandbox_session_id:
            self._emit_system_error(conversation.id, '该会话没有可用的沙箱容器。')
            return

        moderator = next(
            (p for p in agent_participants if p.participant_id == MODERATOR_AGENT_ID),
            None,
        )
        workers = [p for p in agent_participants if p.participant_id != MODERATOR_AGENT_ID]
        disabled_worker_ids = self._disabled_session_agent_ids(agent_configs)
        enabled_workers = [p for p in workers if str(p.participant_id) not in disabled_worker_ids]
        disabled_workers = [p for p in workers if str(p.participant_id) in disabled_worker_ids]
        if not moderator:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少主持 Agent，请重新创建会话。')
            return
        if not workers:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少 worker Agent。')
            return

        round_id = str(uuid.uuid4())
        if self._is_agent_intro_request(user_content):
            moderator_msg, moderator_run = self._create_agent_message_and_run(
                conversation, moderator, round_id, user_message_id, '主持 Agent 正在安排成员自我介绍...'
            )
            plan = self._build_agent_intro_plan(workers)
            self._finish_moderator_message(moderator_msg.id, moderator_run.id, plan)
            self._emit_run_plan(conversation.id, round_id, moderator_msg.id, plan)
            self._execute_worker_plan(conversation, round_id, user_message_id,
                                      user_content, plan, workers)
            return

        if self._is_team_info_query(user_content):
            moderator_msg, moderator_run = self._create_agent_message_and_run(
                conversation, moderator, round_id, user_message_id, '主持 Agent 正在查看群成员...'
            )
            plan = self._build_team_info_answer(workers, user_content, agent_configs)
            self._finish_moderator_message(moderator_msg.id, moderator_run.id, plan)
            return

        moderator_msg, moderator_run = self._create_agent_message_and_run(
            conversation, moderator, round_id, user_message_id, '主持 Agent 正在拆解任务...'
        )

        try:
            from app.sandbox import get_manager
            plan_prompt = self._build_moderator_plan_prompt(user_content, enabled_workers, disabled_workers)
            result = get_manager().send_message(
                conversation.sandbox_session_id,
                moderator.participant_id,
                plan_prompt,
            )
            if result.get('status') == 'error':
                self._mark_agent_message_failed(
                    moderator_msg.id,
                    moderator_run.id,
                    result.get('error', '主持分派失败，请重试'),
                )
                return

            reply = result.get('reply', '')
            self._mark_agent_message_done_if_active(
                moderator_msg.id,
                moderator_run.id,
                moderator.participant_id,
                reply,
            )
            plan, error = self._parse_moderator_plan(reply, workers)
            if error:
                self._mark_agent_message_failed(moderator_msg.id, moderator_run.id,
                                                f'主持分派失败，请重试：{error}')
                return

            self._replace_message_with_moderator_summary(moderator_msg.id, plan)
            if plan.get('type') == 'answer':
                return

            self._emit_run_plan(conversation.id, round_id, moderator_msg.id, plan)
            self._execute_worker_plan(conversation, round_id, user_message_id,
                                      user_content, plan, workers)
            if plan.get('summary_required') is True:
                self._execute_moderator_summary(conversation, moderator, round_id,
                                                user_message_id, user_content, plan)
        except Exception as e:
            self._mark_agent_message_failed(moderator_msg.id, moderator_run.id,
                                            f'主持分派失败，请重试：{e}')

    def _create_agent_message_and_run(self, conversation, participant, round_id,
                                      parent_message_id, progress_text):
        agent_msg = Message(
            conversation_id=conversation.id,
            sender_type='agent',
            sender_id=participant.participant_id,
            content=progress_text,
            message_type='text',
            parent_message_id=parent_message_id,
            elements=[{'type': 'progress', 'content': progress_text, 'status': 'running'}],
            round_id=round_id,
            status='streaming',
            raw_output='',
        )
        db.session.add(agent_msg)
        db.session.commit()

        run = agent_run_service.create_run(
            conversation_id=conversation.id,
            round_id=round_id,
            message_id=agent_msg.id,
            agent_id=participant.participant_id,
            sandbox_session_id=conversation.sandbox_session_id,
        )
        agent_msg.run_id = run.id
        db.session.commit()

        socketio.emit('conversation_message_created', _message_dict(agent_msg),
                      room=conversation.id)
        return agent_msg, run

    def _build_moderator_plan_prompt(self, user_content, workers):
        worker_lines = []
        for p in workers:
            ws = p.participant_name or p.participant_id
            worker_lines.append(
                f'- agent_id: {p.participant_id}; name: {p.participant_name or p.participant_id}; workspace: /workspace/agents/{ws}'
            )
        return (
            '请基于下面用户任务生成严格 JSON。只输出 JSON，不要输出 Markdown，不要使用代码块。\n\n'
            '你必须先判断用户意图：\n'
            '1. 如果用户是在询问群里有哪些 Agent、每个 Agent 能做什么、协作方式、当前成员信息，'
            '不要分派 worker，直接输出 type=answer。\n'
            '2. 如果用户是在要求完成一个需要执行的任务，输出 type=plan，并只安排必要的 worker，'
            '不需要所有 worker 都参与。\n\n'
            'type=answer 格式：\n'
            '{\n'
            '  "type": "answer",\n'
            '  "summary": "直接给用户看的简短回答",\n'
            '  "team": [\n'
            '    {"agent_id": "moderator", "name": "任务主持人", "capabilities": ["任务拆分", "调度", "汇总"]}\n'
            '  ]\n'
            '}\n\n'
            'type=plan 格式：\n'
            '{\n'
            '  "type": "plan",\n'
            '  "summary": "我看到团队中有这些 Agent。现在我会安排其中的哪些 Agent 处理什么任务。",\n'
            '  "selected_agents": ["agent_id"],\n'
            '  "tasks": [\n'
            '    {"task_id": "task-id", "agent_id": "agent_id", "title": "任务标题", "instruction": "完整执行指令", "depends_on": [], "can_parallel": true}\n'
            '  ],\n'
            '  "parallel_groups": [["task-id"]],\n'
            '  "summary_required": true\n'
            '}\n\n'
            '可用 worker_agents:\n'
            + '\n'.join(worker_lines)
            + '\n\n用户任务:\n'
            + user_content
        )

    def _parse_moderator_plan(self, reply, workers):
        text = (reply or '').strip()
        if not text:
            return None, '主持 Agent 未返回计划'
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end + 1]
        try:
            plan = json.loads(text)
        except Exception as e:
            return None, f'计划 JSON 解析失败：{e}'

        if isinstance(plan.get('plan'), dict) and not isinstance(plan.get('tasks'), list):
            nested_plan = plan.get('plan') or {}
            title = nested_plan.get('title') or plan.get('title') or '主持 Agent 已形成处理思路'
            steps = nested_plan.get('steps') if isinstance(nested_plan.get('steps'), list) else []
            summary_lines = [str(title)]
            if steps:
                summary_lines.append('')
                summary_lines.append('主持 Agent 的处理思路：')
                for step in steps[:8]:
                    if isinstance(step, dict):
                        action = step.get('action') or step.get('title') or step.get('purpose') or step.get('id')
                        purpose = step.get('purpose') or step.get('description') or ''
                        line = f'- {action}'
                        if purpose and str(purpose) != str(action):
                            line += f'：{purpose}'
                        summary_lines.append(line)
            expected = nested_plan.get('expected_output')
            if expected:
                summary_lines.append('')
                summary_lines.append(f'预期输出：{expected}')
            return {
                'type': 'answer',
                'summary': '\n'.join(summary_lines).strip(),
                'team': self._default_team_info(workers),
                'tasks': [],
                'parallel_groups': [],
                'summary_required': False,
            }, None

        worker_ids = {p.participant_id for p in workers}
        plan_type = str(plan.get('type') or '').strip().lower()
        if not plan_type:
            plan_type = 'plan' if isinstance(plan.get('tasks'), list) else 'answer'

        if plan_type == 'answer':
            summary = str(
                plan.get('summary') or plan.get('answer') or plan.get('goal') or plan.get('note') or ''
            )
            return {
                'type': 'answer',
                'summary': summary,
                'team': plan.get('team') if isinstance(plan.get('team'), list) else self._default_team_info(workers),
                'tasks': [],
                'parallel_groups': [],
                'summary_required': False,
            }, None

        if plan_type != 'plan':
            return None, f'未知主持输出类型：{plan_type}'

        tasks = plan.get('tasks')
        if not isinstance(tasks, list) or not tasks:
            return None, '计划中缺少 tasks'

        normalized_tasks = []
        seen = set()
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                return None, 'tasks 中存在非对象元素'
            task_id = str(task.get('task_id') or f'task-{index + 1}').strip()
            agent_id = str(task.get('agent_id') or '').strip()
            if not task_id:
                return None, 'task_id 不能为空'
            if task_id in seen:
                return None, f'task_id 重复：{task_id}'
            if agent_id not in worker_ids:
                return None, f'未知 worker agent_id：{agent_id}'
            seen.add(task_id)
            depends_on = task.get('depends_on') or []
            if not isinstance(depends_on, list):
                return None, f'{task_id}.depends_on 必须是数组'
            normalized_tasks.append({
                'task_id': task_id,
                'agent_id': agent_id,
                'title': str(task.get('title') or task_id),
                'instruction': str(task.get('instruction') or '').strip() or str(task.get('title') or task_id),
                'depends_on': [str(dep) for dep in depends_on],
                'can_parallel': bool(task.get('can_parallel', True)),
            })

        task_ids = {task['task_id'] for task in normalized_tasks}
        for task in normalized_tasks:
            missing = [dep for dep in task['depends_on'] if dep not in task_ids]
            if missing:
                return None, f'{task["task_id"]} 依赖不存在的任务：{", ".join(missing)}'

        groups = plan.get('parallel_groups')
        if not isinstance(groups, list) or not groups:
            groups = [[task['task_id']] for task in normalized_tasks]
        normalized_groups = []
        grouped = set()
        for group in groups:
            if isinstance(group, str):
                group = [group]
            if not isinstance(group, list):
                return None, 'parallel_groups 中存在非数组元素'
            clean_group = []
            group_agent_ids = set()
            for task_id in group:
                task_id = str(task_id)
                if task_id not in task_ids:
                    return None, f'parallel_groups 引用了未知任务：{task_id}'
                task_agent_id = next(
                    task['agent_id'] for task in normalized_tasks
                    if task['task_id'] == task_id
                )
                if task_agent_id in group_agent_ids:
                    return None, f'同一个并行组不能给同一 Agent 分配多个任务：{task_agent_id}'
                group_agent_ids.add(task_agent_id)
                if task_id not in clean_group:
                    clean_group.append(task_id)
                    grouped.add(task_id)
            if clean_group:
                normalized_groups.append(clean_group)
        for task in normalized_tasks:
            if task['task_id'] not in grouped:
                normalized_groups.append([task['task_id']])

        return {
            'type': 'plan',
            'workflow_name': str(plan.get('workflow_name') or plan.get('name') or ''),
            'summary': str(plan.get('summary') or ''),
            'selected_agents': list(dict.fromkeys(
                str(agent_id) for agent_id in (plan.get('selected_agents') or [])
                if str(agent_id) in worker_ids
            )) or list(dict.fromkeys(task['agent_id'] for task in normalized_tasks)),
            'tasks': normalized_tasks,
            'parallel_groups': normalized_groups,
            'summary_required': bool(plan.get('summary_required', False)),
        }, None

    @staticmethod
    def _default_team_info(workers, agent_configs=None):
        config_map = MessageService._normalize_session_agent_configs(agent_configs)
        team = [{
            'agent_id': MODERATOR_AGENT_ID,
            'name': '任务主持人',
            'capabilities': ['理解用户任务', '选择合适的 Agent', '安排并行或串行执行', '汇总执行结果'],
        }]
        for worker in workers:
            team.append({
                'agent_id': worker.participant_id,
                'name': worker.participant_name or worker.participant_id,
                'capabilities': ['根据自身角色完成主持 Agent 分配的任务'],
            })
        return team

    def _replace_message_with_moderator_summary(self, message_id, plan):
        msg = Message.query.get(message_id)
        if not msg:
            return
        from app.models.agent_run import AgentRun
        run = AgentRun.query.get(msg.run_id)
        if plan.get('type') == 'answer':
            content = self._format_team_answer(plan)
        else:
            content = self._format_plan_summary(plan)
        msg.content = content
        msg.elements = self._moderator_plan_elements(msg.elements, content, plan)
        msg.raw_output = ''
        msg.status = 'done'
        if run:
            run.status = 'done'
            run.finished_at = beijing_now()
        db.session.commit()
        socketio.emit('conversation_message_status', {
            'conversation_id': msg.conversation_id,
            'message_id': msg.id,
            'run_id': msg.run_id,
            'agent_id': msg.sender_id,
            'status': 'done',
            'content': msg.content,
            'elements': msg.elements,
            'raw_output': msg.raw_output,
            'clear_raw_output': True,
            'sender_name': self._sender_name_for_message(msg),
        }, room=msg.conversation_id)

    @staticmethod
    def _moderator_plan_elements(existing_elements, content, plan):
        preserved_types = {'result', 'summary', 'error', 'code', 'table', 'image', 'file', 'service', 'workflow'}
        elements = [{
            'type': 'text',
            'content': content,
            'data': {'kind': 'moderator_plan_summary'},
        }]
        for element in existing_elements or []:
            if not isinstance(element, dict):
                continue
            data = element.get('data') if isinstance(element.get('data'), dict) else {}
            if data.get('kind') in {'moderator_plan_summary', 'moderator_plan_json'}:
                continue
            if element.get('type') in preserved_types:
                elements.append(element)
        if plan.get('type') == 'plan':
            workflow = MessageService._workflow_from_plan(plan)
            elements.append({
                'type': 'workflow',
                'content': json.dumps(workflow, ensure_ascii=False),
                'data': workflow,
            })
            elements.append({
                'type': 'code',
                'content': json.dumps(plan, ensure_ascii=False, indent=2),
                'data': {
                    'kind': 'moderator_plan_json',
                    'title': workflow.get('name') or '任务分派工作流',
                    'language': 'json',
                    'filename': 'moderator-plan.json',
                    'workflow': workflow,
                },
            })
        return elements

    @staticmethod
    def _workflow_from_plan(plan):
        tasks = plan.get('tasks') if isinstance(plan.get('tasks'), list) else []
        groups = plan.get('parallel_groups') if isinstance(plan.get('parallel_groups'), list) else []
        stage_by_task = {}
        for stage_index, group in enumerate(groups):
            if not isinstance(group, list):
                continue
            for order_index, task_id in enumerate(group):
                stage_by_task[str(task_id)] = (stage_index, order_index)
        nodes = []
        for index, task in enumerate(tasks):
            task_id = str(task.get('task_id') or f'task-{index + 1}')
            stage_index, order_index = stage_by_task.get(task_id, (index, 0))
            nodes.append({
                'id': task_id,
                'task_id': task_id,
                'agent_id': task.get('agent_id') or '',
                'title': task.get('title') or task_id,
                'instruction': task.get('instruction') or '',
                'depends_on': task.get('depends_on') or [],
                'can_parallel': bool(task.get('can_parallel', True)),
                'x': 80 + stage_index * 240,
                'y': 80 + order_index * 130,
            })
        edges = []
        for task in tasks:
            target = str(task.get('task_id') or '')
            for dep in task.get('depends_on') or []:
                if target and dep:
                    edges.append({'from': str(dep), 'to': target})
        if not edges and len(groups) > 1:
            for index in range(len(groups) - 1):
                left = groups[index] if isinstance(groups[index], list) else []
                right = groups[index + 1] if isinstance(groups[index + 1], list) else []
                for from_id in left:
                    for to_id in right:
                        edges.append({'from': str(from_id), 'to': str(to_id)})
        first_title = nodes[0].get('title') if nodes else ''
        name = plan.get('workflow_name') or plan.get('name') or (f'{first_title}工作流' if first_title else '任务分派工作流')
        return {
            'id': str(uuid.uuid4()),
            'name': str(name)[:32],
            'summary': plan.get('summary') or '',
            'nodes': nodes,
            'edges': edges,
            'parallel_groups': groups,
            'source': 'moderator_plan',
        }

    @staticmethod
    def _format_team_answer(plan):
        lines = []
        summary = (plan.get('summary') or '').strip()
        if summary:
            lines.append(summary)
            lines.append('')
        lines.append('我看到当前群聊中有这些 Agent：')
        if summary.startswith('下面是你询问') and len(lines) >= 3:
            lines.pop()
        if summary.startswith('下面是你询问') and len(lines) >= 3:
            lines.pop()
        for item in plan.get('team') or []:
            name = item.get('name') or item.get('agent_id') or 'Agent'
            agent_id = item.get('agent_id') or ''
            lines.append(f'- **{name}** (`{agent_id}`)')
            capabilities = item.get('capabilities') or []
            for capability in capabilities[:5]:
                lines.append(f'  - {capability}')
            skill = str(item.get('skill') or '').strip()
            if skill:
                skill_label = '会话级 skill' if item.get('session_overridden') else 'skill'
                lines.append(f'  - **{skill_label}**:')
                for line in skill.splitlines():
                    if line.strip():
                        lines.append(f'    {line.strip()}')
        return '\n'.join(lines).strip()

    @staticmethod
    def _format_plan_summary(plan):
        lines = []
        summary = (plan.get('summary') or '').strip()
        if summary:
            lines.append(summary)
        selected = plan.get('selected_agents') or []
        if selected:
            lines.append('')
            lines.append('本轮我会安排这些 Agent 参与：')
            for agent_id in selected:
                lines.append(f'- `{agent_id}`')
        tasks = plan.get('tasks') or []
        if tasks:
            lines.append('')
            lines.append('分工如下：')
            for task in tasks:
                deps = task.get('depends_on') or []
                dep_text = f'，依赖：{", ".join(deps)}' if deps else ''
                lines.append(
                    f'- **{task.get("title") or task.get("task_id")}** -> `{task.get("agent_id")}`{dep_text}'
                )
        groups = plan.get('parallel_groups') or []
        if groups:
            lines.append('')
            lines.append('执行顺序：')
            for index, group in enumerate(groups, start=1):
                lines.append(f'{index}. ' + '、'.join(f'`{item}`' for item in group))
        return '\n'.join(lines).strip() or '主持 Agent 已生成分工计划。'

    def _build_moderator_plan_prompt(self, user_content, workers, disabled_workers=None):
        worker_lines = []
        for p in workers:
            profile = self._worker_profile(p)
            capabilities = profile.get('capabilities') or []
            capability_text = '、'.join(capabilities) if capabilities else '未配置能力标签'
            skill = (profile.get('skill') or '未配置 skill')[:500]
            worker_lines.append(
                f"- agent_id: {profile['agent_id']}\n"
                f"  name: {profile['name']}\n"
                f"  capabilities: {capability_text}\n"
                f"  skill: {skill}"
            )
        disabled_lines = []
        for p in disabled_workers or []:
            profile = self._worker_profile(p)
            disabled_lines.append(f"- agent_id: {profile['agent_id']}\n  name: {profile['name']}")
        enabled_text = "\n".join(worker_lines) if worker_lines else "无"
        disabled_text = "\n".join(disabled_lines) if disabled_lines else "无"
        return (
            "请基于下面用户任务生成严格 JSON。只输出 JSON，不要输出 Markdown，不要使用代码块。\n\n"
            "你必须先判断自己是否能回答：\n"
            "1. 如果用户询问群里有哪些 Agent、各自能做什么、协作方式、当前成员信息，并且 worker_agents 已提供足够的名称/能力/skill，"
            "你应直接回答，输出 type=answer，不要分派 worker。\n"
            "2. 如果用户询问成员能力，但 worker_agents 的能力信息不足以回答，你应输出 type=plan。summary 必须先说："
            "我知道群里有哪些 agent，但不清楚他们具体能干啥，我帮你问一下他们。"
            "然后给每个需要了解的 worker 生成一个自我介绍任务。\n"
            "3. 如果用户要求完成一个需要执行的任务，输出 type=plan，只安排必要的 worker，不需要所有 worker 都参与。\n\n"
            "4. disabled_worker_agents 是当前会话中被用户禁用的 Agent。你不能把任务分配给这些 Agent，"
            "也不能把它们写入 selected_agents 或 tasks.agent_id。"
            "如果用户任务必须依赖某个被禁用 Agent，或当前启用的 worker 无法完成任务，输出 type=answer，"
            "告诉用户需要先在“智能体配置”中启用对应 Agent 后再继续。\n\n"
            "type=answer 格式：\n"
            "{\n"
            '  "type": "answer",\n'
            '  "summary": "直接给用户看的简短回答",\n'
            '  "team": [\n'
            '    {"agent_id": "moderator", "name": "任务主持人", "capabilities": ["任务拆分", "调度", "汇总"]}\n'
            "  ]\n"
            "}\n\n"
            "type=plan 格式：\n"
            "{\n"
            '  "type": "plan",\n'
            '  "workflow_name": "简短工作流名称，建议 6 到 16 个字",\n'
            '  "summary": "给用户看的主持说明：我看到团队中有哪些 Agent，现在安排哪些 Agent 处理什么任务。",\n'
            '  "selected_agents": ["agent_id"],\n'
            '  "tasks": [\n'
            '    {"task_id": "task-id", "agent_id": "agent_id", "title": "任务标题", "instruction": "完整执行指令", "depends_on": [], "can_parallel": true}\n'
            "  ],\n"
            '  "parallel_groups": [["task-id"]],\n'
            '  "summary_required": true\n'
            "}\n\n"
            "要求：\n"
            "- type=plan 时 tasks 必须至少有 1 个元素。\n"
            "- type=plan 时必须提供简短 workflow_name，用于工作流图标题。\n"
            "- type=answer 时 tasks 可以省略，也可以是空数组。\n"
            "- agent_id 必须来自 worker_agents，不要编造。\n\n"
            "可用 worker_agents:\n"
            + enabled_text
            + "\n\n禁用 disabled_worker_agents:\n"
            + disabled_text
            + "\n\n用户任务:\n"
            + user_content
        )

    @staticmethod
    def _worker_profile(participant):
        agent = Agent.query.get(participant.participant_id)
        capabilities = []
        skill = ''
        name = participant.participant_name or participant.participant_id
        if agent:
            capabilities = agent.capability_tags or []
            skill = agent.skill or ''
            name = participant.participant_name or agent.name or participant.participant_id
        return {
            'agent_id': participant.participant_id,
            'name': name,
            'capabilities': capabilities,
            'skill': skill,
        }

    def _parse_moderator_plan(self, reply, workers):
        text = (reply or '').strip()
        if not text:
            return None, '主持 Agent 未返回计划'
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end + 1]
        try:
            plan = json.loads(text)
        except Exception as e:
            return None, f'计划 JSON 解析失败：{e}'

        worker_ids = {p.participant_id for p in workers}
        plan_type = str(plan.get('type') or '').strip().lower()
        if not plan_type:
            raw_tasks = plan.get('tasks')
            plan_type = 'plan' if isinstance(raw_tasks, list) and len(raw_tasks) > 0 else 'answer'

        if plan_type == 'answer':
            summary = str(
                plan.get('summary') or plan.get('answer') or plan.get('goal') or plan.get('note') or ''
            )
            return {
                'type': 'answer',
                'summary': summary,
                'team': plan.get('team') if isinstance(plan.get('team'), list) else self._default_team_info(workers),
                'tasks': [],
                'parallel_groups': [],
                'summary_required': False,
            }, None

        if plan_type != 'plan':
            return None, f'未知主持输出类型：{plan_type}'

        tasks = plan.get('tasks')
        if not isinstance(tasks, list) or not tasks:
            summary = str(plan.get('summary') or plan.get('answer') or '').strip()
            if summary:
                return {
                    'type': 'answer',
                    'summary': summary,
                    'team': plan.get('team') if isinstance(plan.get('team'), list) else self._default_team_info(workers),
                    'tasks': [],
                    'parallel_groups': [],
                    'summary_required': False,
                }, None
            return None, '计划中缺少 tasks'

        normalized_tasks = []
        seen = set()
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                return None, 'tasks 中存在非对象元素'
            task_id = str(task.get('task_id') or f'task-{index + 1}').strip()
            agent_id = str(task.get('agent_id') or '').strip()
            if not task_id:
                return None, 'task_id 不能为空'
            if task_id in seen:
                return None, f'task_id 重复：{task_id}'
            if agent_id not in worker_ids:
                return None, f'未知 worker agent_id：{agent_id}'
            seen.add(task_id)
            depends_on = task.get('depends_on') or []
            if not isinstance(depends_on, list):
                return None, f'{task_id}.depends_on 必须是数组'
            normalized_tasks.append({
                'task_id': task_id,
                'agent_id': agent_id,
                'title': str(task.get('title') or task_id),
                'instruction': str(task.get('instruction') or '').strip() or str(task.get('title') or task_id),
                'depends_on': [str(dep) for dep in depends_on],
                'can_parallel': bool(task.get('can_parallel', True)),
            })

        task_ids = {task['task_id'] for task in normalized_tasks}
        for task in normalized_tasks:
            missing = [dep for dep in task['depends_on'] if dep not in task_ids]
            if missing:
                return None, f'{task["task_id"]} 依赖不存在的任务：{", ".join(missing)}'

        groups = plan.get('parallel_groups')
        if not isinstance(groups, list) or not groups:
            groups = [[task['task_id']] for task in normalized_tasks]
        normalized_groups = []
        grouped = set()
        for group in groups:
            if isinstance(group, str):
                group = [group]
            if not isinstance(group, list):
                return None, 'parallel_groups 中存在非数组元素'
            clean_group = []
            group_agent_ids = set()
            for task_id in group:
                task_id = str(task_id)
                if task_id not in task_ids:
                    return None, f'parallel_groups 引用了未知任务：{task_id}'
                task_agent_id = next(
                    task['agent_id'] for task in normalized_tasks
                    if task['task_id'] == task_id
                )
                if task_agent_id in group_agent_ids:
                    return None, f'同一个并行组不能给同一 Agent 分配多个任务：{task_agent_id}'
                group_agent_ids.add(task_agent_id)
                if task_id not in clean_group:
                    clean_group.append(task_id)
                    grouped.add(task_id)
            if clean_group:
                normalized_groups.append(clean_group)
        for task in normalized_tasks:
            if task['task_id'] not in grouped:
                normalized_groups.append([task['task_id']])

        return {
            'type': 'plan',
            'workflow_name': str(plan.get('workflow_name') or plan.get('name') or ''),
            'summary': str(plan.get('summary') or ''),
            'selected_agents': list(dict.fromkeys(
                str(agent_id) for agent_id in (plan.get('selected_agents') or [])
                if str(agent_id) in worker_ids
            )) or list(dict.fromkeys(task['agent_id'] for task in normalized_tasks)),
            'tasks': normalized_tasks,
            'parallel_groups': normalized_groups,
            'summary_required': bool(plan.get('summary_required', False)),
        }, None

    @staticmethod
    def _default_team_info(workers, agent_configs=None):
        config_map = MessageService._normalize_session_agent_configs(agent_configs)
        team = [{
            'agent_id': MODERATOR_AGENT_ID,
            'name': '任务主持人',
            'capabilities': ['理解用户任务', '选择合适的 Agent', '安排并行或串行执行', '汇总执行结果'],
        }]
        for worker in workers:
            profile = MessageService._worker_profile(worker)
            session_cfg = config_map.get(str(worker.participant_id)) or {}
            skill = session_cfg.get('skill') or profile.get('skill') or ''
            team.append({
                'agent_id': worker.participant_id,
                'name': session_cfg.get('role') or profile['name'],
                'skill': skill,
                'session_overridden': bool(session_cfg),
                'capabilities': profile['capabilities'] or ['根据自身角色完成主持 Agent 分配的任务'],
            })
        return team

    @staticmethod
    def _format_team_answer(plan):
        lines = []
        summary = (plan.get('summary') or '').strip()
        if summary:
            lines.append(summary)
            lines.append('')
        lines.append('我看到当前群聊中有这些 Agent：')
        for item in plan.get('team') or []:
            name = item.get('name') or item.get('agent_id') or 'Agent'
            agent_id = item.get('agent_id') or ''
            lines.append(f'- **{name}** (`{agent_id}`)')
            capabilities = item.get('capabilities') or []
            for capability in capabilities[:5]:
                lines.append(f'  - {capability}')
            skill = str(item.get('skill') or '').strip()
            if skill:
                skill_label = '会话级 skill' if item.get('session_overridden') else 'skill'
                lines.append(f'  - **{skill_label}**:')
                for line in skill.splitlines():
                    if line.strip():
                        lines.append(f'    {line.strip()}')
        return '\n'.join(lines).strip()

    @staticmethod
    def _format_plan_summary(plan):
        lines = []
        summary = (plan.get('summary') or '').strip()
        if summary:
            lines.append(summary)
        selected = plan.get('selected_agents') or []
        if selected:
            lines.append('')
            lines.append('本轮我会安排这些 Agent 参与：')
            for agent_id in selected:
                lines.append(f'- `{agent_id}`')
        tasks = plan.get('tasks') or []
        if tasks:
            lines.append('')
            lines.append('分工如下：')
            for task in tasks:
                deps = task.get('depends_on') or []
                dep_text = f'，依赖：{", ".join(deps)}' if deps else ''
                lines.append(
                    f'- **{task.get("title") or task.get("task_id")}** -> `{task.get("agent_id")}`{dep_text}'
                )
        groups = plan.get('parallel_groups') or []
        if groups:
            lines.append('')
            lines.append('执行顺序：')
            for index, group in enumerate(groups, start=1):
                lines.append(f'{index}. ' + '、'.join(f'`{item}`' for item in group))
        return '\n'.join(lines).strip() or '主持 Agent 已生成分工计划。'

    @staticmethod
    def _is_team_info_query(content):
        text = MessageService._strip_session_config_context(content).lower()
        if ('skill' in text or '技能' in text or '介绍' in text) and not any(
            word in text for word in ('群里', '团队', '成员', '所有agent', '所有 agent', '有哪些agent', '有哪些 agent')
        ):
            return False
        if MessageService._is_skill_query(text):
            return True
        team_words = ('群里', '团队', '成员', 'agent', 'agents', '智能体')
        info_words = ('都有谁', '有哪些', '能做什么', '能干啥', '能力', '职责', '介绍')
        return any(word in text for word in team_words) and any(word in text for word in info_words)

    @staticmethod
    def _strip_session_config_context(content):
        text = str(content or '')
        marker = 'SESSION_AGENT_CONFIG_CONTEXT:'
        if marker in text:
            return text.split(marker, 1)[0].strip()
        json_marker = 'SESSION_AGENT_CONFIG_JSON:'
        if json_marker in text:
            return text.split(json_marker, 1)[0].strip()
        return text

    @staticmethod
    def _is_skill_query(text):
        text = str(text or '').lower()
        return ('skill' in text or '技能' in text) and any(
            word in text for word in ('介绍', '说', '说明', '有哪些', '是什么', '查看', '再讲', '再次')
        )

    @staticmethod
    def _team_item_matches_query(item, query_text):
        query_text = str(query_text or '').lower()
        if not query_text:
            return False
        candidates = [
            item.get('agent_id'),
            item.get('name'),
            ' '.join(item.get('capabilities') or []),
        ]
        for value in candidates:
            value_text = str(value or '').lower().strip()
            if not value_text:
                continue
            if value_text in query_text or query_text in value_text:
                return True
            if any(value_text[index:index + 2] in query_text for index in range(max(len(value_text) - 1, 0))):
                return True
        return False

    def _build_team_info_answer(self, workers, query='', agent_configs=None):
        team = self._default_team_info(workers, agent_configs)
        query_text = self._strip_session_config_context(query).lower()
        worker_team = [item for item in team if item.get('agent_id') != MODERATOR_AGENT_ID]
        matched = [item for item in worker_team if self._team_item_matches_query(item, query_text)]
        if matched:
            team = matched
        worker_names = [
            item.get('name') or item.get('agent_id')
            for item in team
            if item.get('agent_id') != MODERATOR_AGENT_ID
        ]
        summary = (
            f"我看到当前群聊中共有 {len(team)} 个 Agent：1 个任务主持人"
            f"和 {max(len(team) - 1, 0)} 个 worker Agent。"
        )
        if worker_names:
            summary += " 当前 worker 包括：" + "、".join(worker_names) + "。"
        if matched and self._is_skill_query(query_text):
            summary = '下面是你询问的 Agent skill。'
        elif matched:
            summary = '下面是你询问的 Agent 信息。'
        return {
            'type': 'answer',
            'summary': summary,
            'team': team,
            'tasks': [],
            'parallel_groups': [],
            'summary_required': False,
        }

    @staticmethod
    def _is_agent_intro_request(content):
        text = (content or '').lower()
        ask_words = ('让他们', '叫他们', '让它们', '叫它们', '每个agent', '每个 agent', '所有agent', '所有 agent', '他们')
        intro_words = ('介绍自己', '自我介绍', '介绍一下自己', '说说自己', '各自介绍')
        return any(word in text for word in ask_words) and any(word in text for word in intro_words)

    def _build_agent_intro_plan(self, workers):
        tasks = []
        groups = []
        selected = []
        for index, worker in enumerate(workers, start=1):
            profile = self._worker_profile(worker)
            task_id = f'introduce-{index}'
            selected.append(worker.participant_id)
            tasks.append({
                'task_id': task_id,
                'agent_id': worker.participant_id,
                'title': f'{profile["name"]} 自我介绍',
                'instruction': (
                    '请以第一人称向用户介绍你自己。必须说明：'
                    '1. 你的名字和角色；'
                    '2. 你擅长完成哪些任务；'
                    '3. 你在本群聊协作中适合承担什么工作；'
                    '4. 如果需要生成文件，你会优先写入自己的私有工作目录。'
                    '不要替其他 Agent 发言。'
                ),
                'depends_on': [],
                'can_parallel': True,
            })
            groups.append(task_id)
        return {
            'type': 'plan',
            'summary': '我会让每个 worker Agent 分别介绍自己，不由主持人代答。',
            'selected_agents': selected,
            'tasks': tasks,
            'parallel_groups': [groups] if groups else [],
            'summary_required': False,
        }

    def _finish_moderator_message(self, message_id, run_id, plan):
        msg = Message.query.get(message_id)
        if not msg:
            return
        from app.models.agent_run import AgentRun
        run = AgentRun.query.get(run_id)
        content = self._format_team_answer(plan) if plan.get('type') == 'answer' else self._format_plan_summary(plan)
        msg.content = content
        msg.elements = [{'type': 'text', 'content': content}]
        msg.status = 'done'
        msg.raw_output = ''
        if run:
            run.status = 'done'
            run.finished_at = beijing_now()
        db.session.commit()
        socketio.emit('conversation_message_status', {
            'conversation_id': msg.conversation_id,
            'message_id': msg.id,
            'run_id': msg.run_id,
            'agent_id': msg.sender_id,
            'status': 'done',
            'content': msg.content,
            'elements': msg.elements,
            'raw_output': msg.raw_output,
            'replace_elements': True,
            'sender_name': self._sender_name_for_message(msg),
        }, room=msg.conversation_id)

    def _emit_run_plan(self, conversation_id, round_id, moderator_message_id, plan):
        socketio.emit('conversation_run_plan', {
            'conversation_id': conversation_id,
            'round_id': round_id,
            'message_id': moderator_message_id,
            'plan': plan,
        }, room=conversation_id)

    def _execute_worker_plan(self, conversation, round_id, user_message_id,
                             user_content, plan, workers):
        worker_map = {p.participant_id: p.participant_id for p in workers}
        task_map = {task['task_id']: task for task in plan.get('tasks', [])}
        task_results = {}
        for group in plan.get('parallel_groups', []):
            threads = []
            group_results = {}
            for task_id in group:
                task = task_map.get(task_id)
                if not task:
                    continue
                failed_deps = [
                    dep for dep in task.get('depends_on', [])
                    if task_results.get(dep, {}).get('status') != 'done'
                ]
                if failed_deps:
                    group_results[task_id] = {
                        'status': 'error',
                        'reply': f'前置任务未成功完成，当前任务未执行：{", ".join(failed_deps)}',
                    }
                    participant = self._get_conversation_participant(
                        conversation.id, worker_map[task['agent_id']]
                    )
                    self._create_skipped_worker_message(conversation, participant,
                                                        round_id, user_message_id, task,
                                                        group_results[task_id]['reply'])
                    continue
                app = current_app._get_current_object()
                thread = threading.Thread(
                    target=self._run_worker_task,
                    args=(app, conversation.id, round_id, user_message_id, user_content,
                          task, worker_map[task['agent_id']], group_results),
                    daemon=True,
                )
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
            task_results.update(group_results)

    def _run_worker_task(self, app, conversation_id, round_id, user_message_id,
                         user_content, task, participant_id, result_bucket):
        with app.app_context():
            conversation = conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return
            participant = self._get_conversation_participant(conversation_id, participant_id)
            if not participant:
                result_bucket[task['task_id']] = {
                    'status': 'error',
                    'reply': f'Agent not found in conversation: {participant_id}',
                }
                return
            agent_msg, run = self._create_agent_message_and_run(
                conversation, participant, round_id, user_message_id,
                f'正在执行：{task["title"]}'
            )
            prompt = (
                f'用户原始任务：\n{user_content}\n\n'
                f'主持 Agent 分配给你的任务：\n'
                f'- 标题：{task["title"]}\n'
                f'- 指令：{task["instruction"]}\n\n'
                '请只完成分配给你的部分。需要生成文件时必须写入你的私有工作目录。'
            )
            try:
                from app.sandbox import get_manager
                result = get_manager().send_message(
                    conversation.sandbox_session_id,
                    participant.participant_id,
                    prompt,
                )
                if result.get('status') == 'error':
                    result = self._retry_agent_after_model_error(
                        conversation, participant.participant_id, prompt, result
                    )
                if result.get('status') == 'error':
                    error = result.get('error', 'Agent execution failed')
                    self._mark_agent_message_failed(agent_msg.id, run.id, error)
                    result_bucket[task['task_id']] = {'status': 'error', 'reply': error}
                else:
                    reply = result.get('reply', '')
                    self._mark_agent_message_done_if_active(
                        agent_msg.id, run.id, participant.participant_id, reply
                    )
                    result_bucket[task['task_id']] = {'status': 'done', 'reply': reply}
            except Exception as e:
                error = str(e)
                self._mark_agent_message_failed(agent_msg.id, run.id, error)
                result_bucket[task['task_id']] = {'status': 'error', 'reply': error}

    def _create_skipped_worker_message(self, conversation, participant, round_id,
                                       user_message_id, task, reason):
        if not participant:
            return
        agent_msg, run = self._create_agent_message_and_run(
            conversation, participant, round_id, user_message_id, reason
        )
        self._mark_agent_message_failed(agent_msg.id, run.id, reason)

    def _retry_agent_after_model_error(self, conversation, agent_id, message, result):
        error = (result or {}).get('error') or (result or {}).get('reply') or ''
        if not self._is_model_runtime_error(error):
            return result
        try:
            from app.services.settings_service import settings_service
            from app.sandbox import get_manager
            env_vars, env_error = settings_service.get_container_env_vars(conversation.owner_id)
            if env_error:
                return {
                    'status': 'error',
                    'error': f'{error}\n刷新模型配置失败：{env_error}',
                }
            manager = get_manager()
            manager.update_model_config(conversation.sandbox_session_id, env_vars)
            manager.restart_agent(conversation.sandbox_session_id, agent_id)
            retry = manager.send_message(conversation.sandbox_session_id, agent_id, message)
            if retry.get('status') == 'error':
                retry_error = retry.get('error') or retry.get('reply') or 'Agent execution failed'
                retry['error'] = f'{retry_error}\n已刷新配置并重启 Claude Code 后重试 1 次。'
            return retry
        except Exception as e:
            return {
                'status': 'error',
                'error': f'{error}\n刷新配置并重启 Claude Code 失败：{e}',
            }

    @staticmethod
    def _is_model_runtime_error(error):
        text = str(error or '').lower()
        markers = (
            'api error',
            'insufficient balance',
            '402',
            '401',
            '403',
            'auth',
            'unauthorized',
            'invalid api key',
            'permission',
            'rate limit',
            '429',
            'model',
            'base_url',
            'baseurl',
            'anthropic',
            'claude',
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def _get_conversation_participant(conversation_id, agent_id):
        return next(
            (
                p for p in conversation_repo.get_conversation_participants(conversation_id)
                if p.participant_type == 'agent' and p.participant_id == agent_id
            ),
            None,
        )

    def _execute_moderator_summary(self, conversation, moderator, round_id,
                                   user_message_id, user_content, plan):
        summary_msg, run = self._create_agent_message_and_run(
            conversation, moderator, round_id, user_message_id, '主持 Agent 正在汇总结果...'
        )
        task_lines = []
        for task in plan.get('tasks', []):
            task_lines.append(
                f'- {task["task_id"]} ({task["title"]}) -> {task["agent_id"]}'
            )
        prompt = (
            '请基于本轮 worker Agent 的上下文和输出，为用户生成最终汇总。'
            '不要重新分派任务，不要输出 JSON。\n\n'
            f'用户原始任务：\n{user_content}\n\n'
            f'本轮任务计划：\n' + '\n'.join(task_lines)
        )
        try:
            from app.sandbox import get_manager
            result = get_manager().send_message(
                conversation.sandbox_session_id,
                moderator.participant_id,
                prompt,
            )
            if result.get('status') == 'error':
                self._mark_agent_message_failed(summary_msg.id, run.id,
                                                result.get('error', '主持总结失败'))
            else:
                self._mark_agent_message_done_if_active(
                    summary_msg.id, run.id, moderator.participant_id,
                    result.get('reply', ''),
                )
        except Exception as e:
            self._mark_agent_message_failed(summary_msg.id, run.id, str(e))

    def _dispatch_multi_agent_round(self, conversation, agent_participants,
                                    user_content, user_message_id=None, agent_configs=None):
        if not conversation.sandbox_session_id:
            self._emit_system_error(conversation.id, '该会话没有可用的沙箱容器。')
            return

        moderator = next(
            (p for p in agent_participants if p.participant_id == MODERATOR_AGENT_ID),
            None,
        )
        workers = [p for p in agent_participants if p.participant_id != MODERATOR_AGENT_ID]
        disabled_worker_ids = self._disabled_session_agent_ids(agent_configs)
        enabled_workers = [p for p in workers if str(p.participant_id) not in disabled_worker_ids]
        disabled_workers = [p for p in workers if str(p.participant_id) in disabled_worker_ids]
        if not moderator:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少主持 Agent，请重新创建会话。')
            return
        if not workers:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少 worker Agent。')
            return

        round_id = str(uuid.uuid4())
        moderator_msg, moderator_run = self._create_agent_message_and_run(
            conversation, moderator, round_id, user_message_id, '主持 Agent 正在处理请求...'
        )

        try:
            from app.sandbox import get_manager
            if not enabled_workers:
                plan = self._disabled_workers_answer(disabled_workers)
                self._replace_message_with_moderator_summary(moderator_msg.id, plan)
                return
            plan_prompt = self._build_moderator_plan_prompt(user_content, enabled_workers, disabled_workers)
            reply = ''
            plan = None
            for attempt in range(1, 4):
                result = get_manager().send_message(
                    conversation.sandbox_session_id,
                    moderator.participant_id,
                    plan_prompt,
                )
                if result.get('status') == 'error':
                    error = result.get('error', '主持分派失败')
                    if self._is_retryable_moderator_error(error) and attempt < 3:
                        continue
                    self._mark_agent_message_failed(
                        moderator_msg.id,
                        moderator_run.id,
                        self._format_moderator_retry_error(error, attempt),
                    )
                    return

                candidate_reply = result.get('reply', '')
                plan, error = self._parse_moderator_plan(candidate_reply, workers)
                if not error:
                    reply = candidate_reply
                    break
                if self._is_retryable_moderator_error(error) and attempt < 3:
                    continue
                self._mark_agent_message_failed(
                    moderator_msg.id,
                    moderator_run.id,
                    self._format_moderator_retry_error(error, attempt),
                )
                return

            self._replace_message_with_moderator_summary(moderator_msg.id, plan)
            if plan.get('type') == 'answer':
                return

            self._emit_run_plan(conversation.id, round_id, moderator_msg.id, plan)
            self._execute_worker_plan(conversation, round_id, user_message_id,
                                      user_content, plan, workers)
            if plan.get('summary_required') is True:
                self._execute_moderator_summary(conversation, moderator, round_id,
                                                user_message_id, user_content, plan)
        except Exception as e:
            self._mark_agent_message_failed(
                moderator_msg.id,
                moderator_run.id,
                self._format_moderator_retry_error(str(e), 1),
            )

    def _dispatch_multi_agent_round(self, conversation, agent_participants,
                                    user_content, user_message_id=None, agent_configs=None):
        if not conversation.sandbox_session_id:
            self._emit_system_error(conversation.id, '该会话没有可用的沙箱容器。')
            return

        moderator = next(
            (p for p in agent_participants if p.participant_id == MODERATOR_AGENT_ID),
            None,
        )
        workers = [p for p in agent_participants if p.participant_id != MODERATOR_AGENT_ID]
        disabled_worker_ids = self._disabled_session_agent_ids(agent_configs)
        enabled_workers = [p for p in workers if str(p.participant_id) not in disabled_worker_ids]
        disabled_workers = [p for p in workers if str(p.participant_id) in disabled_worker_ids]
        if not moderator:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少主持 Agent，请重新创建会话。')
            return
        if not workers:
            self._emit_system_error(conversation.id, '多 Agent 会话缺少 worker Agent。')
            return

        round_id = str(uuid.uuid4())
        moderator_msg, moderator_run = self._create_agent_message_and_run(
            conversation, moderator, round_id, user_message_id, '主持 Agent 正在处理请求...'
        )

        try:
            from app.sandbox import get_manager
            plan_prompt = self._build_moderator_plan_prompt(user_content, enabled_workers, disabled_workers)
            reply = ''
            plan = None
            last_parse_error = ''
            for attempt in range(1, 4):
                attempt_prompt = plan_prompt
                if attempt > 1 and last_parse_error:
                    attempt_prompt = (
                        f"{plan_prompt}\n\n"
                        f"上一次输出无法作为任务分派 JSON 解析：{last_parse_error}\n"
                        "请重新输出一个严格合法的 JSON 对象。不要输出 Markdown、代码块或解释文字；"
                        "字符串内部的双引号必须转义，或改用不含双引号的中文表述。"
                    )
                result = get_manager().send_message(
                    conversation.sandbox_session_id,
                    moderator.participant_id,
                    attempt_prompt,
                )
                if result.get('status') == 'error':
                    result = self._retry_agent_after_model_error(
                        conversation, moderator.participant_id, attempt_prompt, result
                    )
                if result.get('status') == 'error':
                    error = result.get('error') or result.get('reply') or '主持分派失败'
                    if self._is_retryable_moderator_error(error) and attempt < 3:
                        continue
                    self._mark_agent_message_failed(
                        moderator_msg.id,
                        moderator_run.id,
                        self._format_moderator_retry_error(error, attempt),
                    )
                    return

                candidate_reply = result.get('reply', '')
                plan, error = self._parse_moderator_plan(candidate_reply, enabled_workers)
                if not error:
                    reply = candidate_reply
                    break
                last_parse_error = error
                if self._is_retryable_moderator_error(error) and attempt < 3:
                    continue
                self._mark_agent_message_failed(
                    moderator_msg.id,
                    moderator_run.id,
                    self._format_moderator_retry_error(error, attempt),
                )
                return

            self._replace_message_with_moderator_summary(moderator_msg.id, plan)
            if plan.get('type') == 'answer':
                return

            self._emit_run_plan(conversation.id, round_id, moderator_msg.id, plan)
            self._execute_worker_plan(conversation, round_id, user_message_id,
                                      user_content, plan, enabled_workers)
            if plan.get('summary_required') is True:
                self._execute_moderator_summary(conversation, moderator, round_id,
                                                user_message_id, user_content, plan)
        except Exception as e:
            self._mark_agent_message_failed(
                moderator_msg.id,
                moderator_run.id,
                self._format_moderator_retry_error(str(e), 1),
            )

    def _parse_moderator_plan(self, reply, workers):
        raw_text = (reply or '').strip()
        if not raw_text:
            return None, '主持 Agent 没有返回内容'

        text = raw_text
        looks_like_plan = self._looks_like_moderator_plan(raw_text)
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end + 1]
            else:
                if looks_like_plan:
                    return None, '计划 JSON 解析失败：未找到完整 JSON 对象'
                return self._moderator_direct_answer(raw_text, workers), None

        try:
            plan = json.loads(text)
        except Exception as e:
            if looks_like_plan:
                return None, f'计划 JSON 解析失败：{e}'
            return self._moderator_direct_answer(raw_text, workers), None

        if isinstance(plan.get('plan'), dict) and not isinstance(plan.get('tasks'), list):
            nested_plan = plan.get('plan') or {}
            title = nested_plan.get('title') or plan.get('title') or '主持 Agent 已形成处理思路'
            steps = nested_plan.get('steps') if isinstance(nested_plan.get('steps'), list) else []
            summary_lines = [str(title)]
            if steps:
                summary_lines.append('')
                summary_lines.append('主持 Agent 的处理思路：')
                for step in steps[:8]:
                    if isinstance(step, dict):
                        action = step.get('action') or step.get('title') or step.get('purpose') or step.get('id')
                        purpose = step.get('purpose') or step.get('description') or ''
                        line = f'- {action}'
                        if purpose and str(purpose) != str(action):
                            line += f'：{purpose}'
                        summary_lines.append(line)
            expected = nested_plan.get('expected_output')
            if expected:
                summary_lines.append('')
                summary_lines.append(f'预期输出：{expected}')
            return self._moderator_direct_answer('\n'.join(summary_lines).strip(), workers), None

        worker_ids = {p.participant_id for p in workers}
        plan_type = str(plan.get('type') or '').strip().lower()
        raw_tasks = plan.get('tasks')
        if not plan_type:
            plan_type = 'plan' if isinstance(raw_tasks, list) and len(raw_tasks) > 0 else 'answer'

        if plan_type == 'answer':
            summary = str(
                plan.get('summary') or plan.get('answer') or plan.get('goal') or plan.get('note') or raw_text
            )
            return {
                'type': 'answer',
                'summary': summary,
                'team': plan.get('team') if isinstance(plan.get('team'), list) else [],
                'tasks': [],
                'parallel_groups': [],
                'summary_required': False,
            }, None

        if plan_type != 'plan':
            return self._moderator_direct_answer(raw_text, workers), None

        tasks = plan.get('tasks')
        if not isinstance(tasks, list) or not tasks:
            summary = str(plan.get('summary') or plan.get('answer') or raw_text).strip()
            return self._moderator_direct_answer(summary, workers), None

        normalized_tasks = []
        seen = set()
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                return self._moderator_direct_answer(raw_text, workers), None
            task_id = str(task.get('task_id') or f'task-{index + 1}').strip()
            agent_id = str(task.get('agent_id') or '').strip()
            if not task_id:
                return None, 'task_id 不能为空'
            if task_id in seen:
                return None, f'task_id 重复：{task_id}'
            if agent_id not in worker_ids:
                return None, f'未知 worker agent_id：{agent_id}'
            seen.add(task_id)
            depends_on = task.get('depends_on') or []
            if not isinstance(depends_on, list):
                return None, f'{task_id}.depends_on 必须是数组'
            normalized_tasks.append({
                'task_id': task_id,
                'agent_id': agent_id,
                'title': str(task.get('title') or task_id),
                'instruction': str(task.get('instruction') or '').strip() or str(task.get('title') or task_id),
                'depends_on': [str(dep) for dep in depends_on],
                'can_parallel': bool(task.get('can_parallel', True)),
            })

        task_ids = {task['task_id'] for task in normalized_tasks}
        for task in normalized_tasks:
            missing = [dep for dep in task['depends_on'] if dep not in task_ids]
            if missing:
                return None, f'{task["task_id"]} 依赖不存在的任务：{", ".join(missing)}'

        groups = plan.get('parallel_groups')
        if not isinstance(groups, list) or not groups:
            groups = [[task['task_id']] for task in normalized_tasks]
        normalized_groups = []
        grouped = set()
        for group in groups:
            if isinstance(group, str):
                group = [group]
            if not isinstance(group, list):
                return None, 'parallel_groups 中存在非数组元素'
            clean_group = []
            group_agent_ids = set()
            for task_id in group:
                task_id = str(task_id)
                if task_id not in task_ids:
                    return None, f'parallel_groups 引用了未知任务：{task_id}'
                task_agent_id = next(
                    task['agent_id'] for task in normalized_tasks
                    if task['task_id'] == task_id
                )
                if task_agent_id in group_agent_ids:
                    return None, f'同一个并行组不能给同一 Agent 分配多个任务：{task_agent_id}'
                group_agent_ids.add(task_agent_id)
                if task_id not in clean_group:
                    clean_group.append(task_id)
                    grouped.add(task_id)
            if clean_group:
                normalized_groups.append(clean_group)
        for task in normalized_tasks:
            if task['task_id'] not in grouped:
                normalized_groups.append([task['task_id']])

        return {
            'type': 'plan',
            'summary': str(plan.get('summary') or ''),
            'selected_agents': list(dict.fromkeys(
                str(agent_id) for agent_id in (plan.get('selected_agents') or [])
                if str(agent_id) in worker_ids
            )) or list(dict.fromkeys(task['agent_id'] for task in normalized_tasks)),
            'tasks': normalized_tasks,
            'parallel_groups': normalized_groups,
            'summary_required': bool(plan.get('summary_required', False)),
        }, None

    def _moderator_direct_answer(self, content, workers):
        return {
            'type': 'answer',
            'summary': (content or '').strip(),
            'team': [],
            'tasks': [],
            'parallel_groups': [],
            'summary_required': False,
        }

    @staticmethod
    def _disabled_workers_answer(disabled_workers):
        names = [
            p.participant_name or p.participant_id
            for p in disabled_workers or []
        ]
        if names:
            summary = (
                '当前会话中可执行的 worker Agent 都已被禁用：'
                + '、'.join(names)
                + '。请先在“智能体配置”中启用需要的 Agent 后再继续。'
            )
        else:
            summary = '当前会话没有可用的已启用 worker Agent。请先在“智能体配置”中启用需要的 Agent 后再继续。'
        return {
            'type': 'answer',
            'summary': summary,
            'team': [],
            'tasks': [],
            'parallel_groups': [],
            'summary_required': False,
        }

    @staticmethod
    def _looks_like_moderator_plan(text):
        lowered = str(text or '').lower()
        markers = (
            '"type"',
            "'type'",
            'type:',
            '"tasks"',
            "'tasks'",
            'tasks:',
            '"parallel_groups"',
            "'parallel_groups'",
            'parallel_groups:',
            '"selected_agents"',
            "'selected_agents'",
            'selected_agents:',
            '"agent_id"',
            "'agent_id'",
            'agent_id:',
            '"task_id"',
            "'task_id'",
            'task_id:',
        )
        if not any(marker in lowered for marker in markers):
            return False
        return any(marker in lowered for marker in ('"plan"', "'plan'", 'type=plan', 'type: plan', 'tasks'))

    @staticmethod
    def _is_retryable_moderator_error(error):
        text = str(error or '').lower()
        retryable_markers = (
            'json',
            'expecting value',
            'timeout',
            'temporarily',
            'connection',
            'network',
            'rate limit',
            '429',
            '402',
            'insufficient balance',
            'api error',
        )
        return any(marker in text for marker in retryable_markers)

    @staticmethod
    def _format_moderator_retry_error(error, attempts):
        text = str(error or '主持分派失败')
        lower = text.lower()
        if '402' in lower or 'insufficient balance' in lower:
            reason = '模型 API 余额不足或额度不可用'
        elif 'json' in lower or 'expecting value' in lower:
            reason = '主持 Agent 没有返回合法的任务分派 JSON'
        else:
            reason = text
        return f'主持分派失败，已重试 {attempts} 次：{reason}。原始错误：{text}'

    @staticmethod
    def _format_team_answer(plan):
        lines = []
        summary = (plan.get('summary') or '').strip()
        if summary:
            lines.append(summary)
            lines.append('')
        if not summary.startswith('下面是你询问'):
            lines.append('我看到当前群聊中有这些 Agent：')
        for item in plan.get('team') or []:
            name = item.get('name') or item.get('agent_id') or 'Agent'
            agent_id = item.get('agent_id') or ''
            lines.append(f'- **{name}** (`{agent_id}`)')
            capabilities = item.get('capabilities') or []
            for capability in capabilities[:5]:
                lines.append(f'  - {capability}')
            skill = str(item.get('skill') or '').strip()
            if skill:
                skill_label = '会话级 skill' if item.get('session_overridden') else 'skill'
                lines.append(f'  - **{skill_label}**:')
                for line in skill.splitlines():
                    if line.strip():
                        lines.append(f'    {line.strip()}')
        return '\n'.join(lines).strip()

    def _emit_system_error(self, conversation_id, content):
        msg = Message(
            conversation_id=conversation_id,
            sender_type='agent',
            sender_id='system',
            content=content,
            message_type='text',
            elements=[{'type': 'progress', 'content': content, 'status': 'error'}],
            status='error',
        )
        db.session.add(msg)
        db.session.commit()
        socketio.emit('conversation_message_created', _message_dict(msg),
                      room=conversation_id)

    def _mark_agent_message_failed(self, message_id, run_id, error):
        msg = Message.query.get(message_id)
        if not msg:
            return
        msg.status = 'error'
        msg.content = error
        msg.raw_output = ((msg.raw_output or '') + f'\n{error}').strip()
        msg.elements = [{'type': 'progress', 'content': error, 'status': 'error'}]
        run = None
        try:
            from app.models.agent_run import AgentRun
            run = AgentRun.query.get(run_id)
        except Exception:
            pass
        if run:
            run.status = 'error'
            run.error = error
            run.finished_at = beijing_now()
        db.session.commit()
        socketio.emit('conversation_message_status', {
            'conversation_id': msg.conversation_id,
            'message_id': msg.id,
            'run_id': run_id,
            'agent_id': msg.sender_id,
            'status': 'error',
            'content': msg.content,
            'elements': msg.elements,
            'raw_output': msg.raw_output,
            'sender_name': self._sender_name_for_message(msg),
            'error': error,
        }, room=msg.conversation_id)

    @staticmethod
    def _sender_name_for_message(msg):
        conversation = conversation_repo.get_by_id(msg.conversation_id)
        if not conversation:
            return msg.sender_id
        participant = next(
            (
                p for p in conversation.participants
                if p.participant_type == msg.sender_type and p.participant_id == msg.sender_id
            ),
            None,
        )
        return participant.participant_name if participant and participant.participant_name else msg.sender_id

    @staticmethod
    def _display_summary_from_raw(text):
        text = (text or '').strip()
        if not text:
            return '任务已完成'
        file_matches = re.findall(
            r'/?workspace/[^\s`\'")\]，。；;]+?\.(?:png|jpe?g|gif|webp|svg|bmp|md|txt|html?|css|js|json|py|pdf|csv|xml|vue|ts)',
            text,
            flags=re.IGNORECASE,
        )
        if file_matches:
            unique = []
            for item in file_matches:
                path = '/' + item.lstrip('/').replace('\\', '/')
                if path not in unique:
                    unique.append(path)
            lines = ['任务已完成，生成/提到的文件：']
            lines.extend(f'- `{path}`' for path in unique[:8])
            if len(unique) > 8:
                lines.append(f'- 另外 {len(unique) - 8} 个文件见 Raw output')
            return '\n'.join(lines)
        if len(text) > 800 or text.count('```') >= 2 or '## /workspace/' in text:
            return '任务已完成。完整输出已折叠到 Raw output。'
        return text

    def _mark_agent_message_done_if_active(self, message_id, run_id, agent_id, reply):
        """Fallback finalization when container event callbacks are missed.

        Normal streaming is driven by sandbox events. The synchronous container
        response is still authoritative enough to close the round if the final
        callback did not reach Flask.
        """
        from app.models.agent_run import AgentRun

        msg = Message.query.get(message_id)
        run = AgentRun.query.get(run_id)
        if not msg or not run or run.status not in ('pending', 'running'):
            return

        text = (reply or '').strip()
        if text:
            msg.content = self._display_summary_from_raw(text)
            if not msg.raw_output:
                msg.raw_output = text

            elements = list(msg.elements or [])
            has_text = any(el.get('type') == 'text' for el in elements if isinstance(el, dict))
            if not has_text:
                elements.append({'type': 'text', 'content': msg.content})
            try:
                from app.services.message_element_builder import mentioned_file_elements
                for element in mentioned_file_elements(run.sandbox_session_id, text):
                    key = element.get('data', {}).get('url') or element.get('data', {}).get('name')
                    exists = key and any(
                        (item.get('data', {}).get('url') or item.get('data', {}).get('name')) == key
                        for item in elements if isinstance(item, dict)
                    )
                    if not exists:
                        elements.append(element)
            except Exception:
                pass
            msg.elements = elements
        elif not msg.content:
            msg.content = '任务已完成'

        msg.status = 'done'
        run.status = 'done'
        run.finished_at = beijing_now()
        db.session.commit()

        socketio.emit('conversation_message_status', {
            'conversation_id': msg.conversation_id,
            'message_id': msg.id,
            'run_id': run.id,
            'agent_id': agent_id,
            'status': 'done',
            'content': msg.content,
            'elements': msg.elements,
            'raw_output': msg.raw_output,
            'sender_name': self._sender_name_for_message(msg),
        }, room=msg.conversation_id)

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
            items.append(_message_dict(msg))

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

        messages = query.order_by(
            Message.created_at.asc(),
            Message.sender_type.desc(),
            Message.id.asc(),
        ).all()
        items = []
        for msg in messages:
            items.append(_message_dict(msg))

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
