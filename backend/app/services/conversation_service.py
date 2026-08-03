from flask import request

from app.models.message import Message
from app.utils.timezone import format_beijing, beijing_now
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_run import AgentRun
from app import db, socketio
from app.repositories.conversation_repo import conversation_repo
from app.repositories.agent_repo import agent_repo
from app.repositories.message_repo import message_repo
from app.services.settings_service import settings_service
from app.services.message_service import _message_dict
MODERATOR_AGENT_ID = 'moderator'

# ── 服务能力摘要缓存 ─────────────────────────────────────
import time as _time
_spec_cache = {}  # {service_name: (spec_dict, expire_time)}

SERVICE_REGISTRY_URLS = {
    "rag":    "http://host.docker.internal:5104",
    "rd":     "http://host.docker.internal:5101",
    "edu":    "http://host.docker.internal:5102",
    "office": "http://host.docker.internal:5103",
}

SERVICE_DISPLAY_NAMES = {
    "rag": "知识库", "rd": "智能研发", "edu": "智慧教育", "office": "智慧办公",
}


def _fetch_service_spec_cached(name, ttl=300):
    """获取服务 spec，带内存缓存（TTL 5分钟）。"""
    import requests as _requests
    now = _time.time()
    if name in _spec_cache:
        cached, expire = _spec_cache[name]
        if now < expire:
            return cached
    base_url = SERVICE_REGISTRY_URLS.get(name, "")
    if not base_url:
        return None
    try:
        resp = _requests.get(f"{base_url}/api/{name}/spec", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            spec = data.get("data", data)
            _spec_cache[name] = (spec, now + ttl)
            return spec
    except Exception:
        pass
    return None


def _build_services_summary(services):
    """根据选中的服务列表，构建能力摘要文本注入 Agent prompt。"""
    if not services:
        return ""
    lines = ["## 可用微服务（用curl + $USER_AUTH_TOKEN直接调用）"]
    idx = 0
    for name in services:
        spec = _fetch_service_spec_cached(name)
        display = SERVICE_DISPLAY_NAMES.get(name, name)
        base_url = SERVICE_REGISTRY_URLS.get(name, f"http://host.docker.internal:5{100 + idx}")
        if not spec:
            lines.append(f"{idx+1}. {name} ({display}): {base_url} — 通过 curl -H 'Authorization: $USER_AUTH_TOKEN' 调用")
            idx += 1
            continue
        idx += 1
        caps = ', '.join(c.get('name', c) if isinstance(c, dict) else str(c)
                        for c in spec.get('capabilities', []))
        lines.append(f"\n{idx}. {name} ({display}): {base_url}")
        if caps:
            lines.append(f"   能力: {caps}")
        popular = spec.get('popular_endpoints', [])
        if popular:
            lines.append("   常用接口:")
            for ep in popular[:5]:
                method = ep.get('method', 'GET')
                path = ep.get('path', '/')
                desc = ep.get('description', '')
                lines.append(f"   curl -s -H 'Authorization: $USER_AUTH_TOKEN' '{base_url}{path}' — {desc}")
    lines.append("\n直接curl获取数据，再回答用户。不要在文件系统中找API数据。")

    # ── 领域特定报告卡片指引（按服务隔离，防止跨领域推送错误类型）──
    if 'rd' in services:
        lines.append("""
## 智能研发(RD)专用报告卡片
RD 数据展示优先级：领域卡片 > table > 纯文本。
查询到需求/缺陷/迭代/项目列表时，**第一优先级：必须**用 weagent-report 逐条发送结构化卡片。
summer 对比/汇总信息可以补充用 table（如"以下是查询汇总"后跟汇总表），但每条具体数据必须先用卡片上报。
只有在卡片无法表达的补充说明才用纯文本，不要用大段 Markdown 列表或表格来替代卡片：
- 需求卡片: weagent-report '{"type":"requirement_card","data":{"id":"<id>","title":"<标题>","project_id":"项目ID","priority":"p0/p1/p2/p3","status":"backlog/todo/in_progress/in_review/done","meta":{"assignee":"负责人","iteration_name":"迭代名"}}}'
- 缺陷卡片: weagent-report '{"type":"bug_card","data":{"id":"<id>","title":"<标题>","project_id":"项目ID","severity":"critical/major/minor/trivial","status":"open/in_progress/fixed/verified/closed","meta":{"assignee":"负责人","iteration_name":"迭代名"}}}'
- 迭代卡片: weagent-report '{"type":"iteration_card","data":{"id":"<id>","title":"<名称>","project_id":"项目ID","status":"planned/active/completed","meta":{"start_date":"开始日期","end_date":"截止日期"},"progress":75}}'
- 项目卡片: weagent-report '{"type":"project_card","data":{"id":"<id>","title":"<项目名>","summary":"<描述>","project_id":"<id>","meta":{"requirement_count":5,"bug_count":3}}"}'
每个卡片独立发送一条 weagent-report，一条消息可以发多个不同类型的卡片。""")
    # 未来扩展: if 'edu' in services: ...  if 'office' in services: ...
    return '\n'.join(lines)


def _build_user_context(user):
    """构建用户身份上下文。"""
    return f"""用户信息:
- 用户名: {user.username}
- 你可以通过 call_service_api 以该用户身份调用微服务 API"""


def _build_rd_base_context():
    """RD 基础上下文（无选定项目时），提供项目管理 CRUD 入口。"""
    return """项目上下文:
- 当前未选定项目，你可以通过 RD 服务 API 列出/创建/查询项目。
- RD服务地址: http://host.docker.internal:5101
- 认证方式: curl -H "Authorization: $USER_AUTH_TOKEN"

常用命令（直接复制到bash执行）：
# 列出所有项目
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects"
# 创建新项目
curl -s -X POST -H "Authorization: $USER_AUTH_TOKEN" -H "Content-Type: application/json" -d '{"name":"项目名","description":"描述"}' "http://host.docker.internal:5101/api/rd/projects"
# 查看单个项目详情
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects/<project_id>"

API返回JSON数据后，用 weagent-report 发送 project_card 或 requirement_card 展示结果。"""


def _build_project_context(project_id):
    """实时查询 RD 项目信息，构建项目上下文。"""
    if not project_id:
        return ""
    try:
        import requests as _requests
        import json as _json
        from flask import current_app
        auth_header = request.headers.get("Authorization", "")
        headers = {"Authorization": auth_header} if auth_header else {}
        base = SERVICE_REGISTRY_URLS.get("rd", "http://host.docker.internal:5101")
        resp = _requests.get(f"{base}/api/rd/projects/{project_id}",
                            headers=headers, timeout=5)
        if resp.status_code != 200:
            return f"项目 ID: {project_id}（服务返回 {resp.status_code}，可通过 API 实时查询）"
        data = resp.json()
        project = data.get("data", data)
        name = project.get('name', project_id)
        desc = project.get('description', '暂无描述')
        req_cnt = project.get('requirement_count', '?')
        bug_cnt = project.get('bug_count', '?')
        iter_cnt = project.get('iteration_count', '?')
        return f"""项目上下文:
- 当前项目: {name} (ID: {project_id})
- 项目描述: {desc}
- 统计: {req_cnt}个需求, {bug_cnt}个缺陷, {iter_cnt}个迭代
- RD服务地址: http://host.docker.internal:5101
- 认证方式: curl -H "Authorization: $USER_AUTH_TOKEN"
- 重要: 项目数据在RD微服务API中，不在文件系统里！直接用curl查询，不要搜索/workspace。

查询命令（直接复制到bash执行）：
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects/{project_id}"
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects/{project_id}/requirements"
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects/{project_id}/bugs"
curl -s -H "Authorization: $USER_AUTH_TOKEN" "http://host.docker.internal:5101/api/rd/projects/{project_id}/iterations"

API返回JSON数据后，根据数据回答用户问题。"""
    except Exception as e:
        from flask import current_app
        current_app.logger.warning(f"查询项目上下文失败 (project_id={project_id}): {e}")
        return f"项目 ID: {project_id}（RD 服务暂不可达，稍后可通过 API 查询）"


def _safe_workspace_name(name):
    import re
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(name or '').strip())
    clean = re.sub(r'\s+', '_', clean).strip('._ ')
    return clean[:80] or 'agent'


def _safe_upload_filename(filename):
    import os
    import re
    raw = str(filename or '').replace('\\', '/').split('/')[-1].strip()
    stem, ext = os.path.splitext(raw)
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', stem)
    stem = re.sub(r'\s+', '_', stem).strip('._ ')
    ext = re.sub(r'[^A-Za-z0-9]', '', ext.lstrip('.'))[:16]
    if not stem:
        stem = 'upload'
    stem = stem[:80]
    return f'{stem}.{ext}' if ext else stem


def _participant_display_info(participant_type, participant_id):
    """Resolve name, avatar, color for a participant.

    Returns dict: {name, avatar, color}
    """
    if participant_type == 'user':
        user = User.query.get(participant_id)
        if user:
            return {
                'name': user.username,
                'avatar': user.avatar_url or '',
                'color': _hash_color(user.username),
            }
        return {'name': participant_id, 'avatar': '', 'color': '#4080ff'}

    elif participant_type == 'agent':
        agent = Agent.query.get(participant_id)
        if agent:
            avatar = agent.avatar_url or ''
            color = agent.avatar_color or _hash_color(agent.name)
            return {
                'name': agent.name,
                'avatar': avatar,
                'color': color,
            }
        # Fallback for unknown agent IDs
        return {'name': participant_id, 'avatar': '', 'color': _hash_color(participant_id)}

    return {'name': participant_id, 'avatar': '', 'color': '#4080ff'}


def _hash_color(name):
    """Deterministic color from a name string."""
    palette = [
        '#2d7ce6', '#47b03a', '#cc7d20', '#d9534f',
        '#8e5cd6', '#2baaa0', '#d9538c', '#e68a2e',
    ]
    if not name:
        return palette[0]
    h = 0
    for ch in name:
        h = ord(ch) + ((h << 5) - h)
    return palette[abs(h) % len(palette)]


def _enrich_participants(participants):
    """Resolve participant display info from stored or DB data.

    Returns a list of dicts: {participant_type, participant_id, name, avatar, color}
    For user participants, always query DB to get the latest avatar_url.
    """
    enriched = []
    for p in participants:
        if p.participant_type == 'user':
            # Always fetch fresh user info so avatar updates reflect immediately
            info = _participant_display_info('user', p.participant_id)
            enriched.append({
                'participant_type': p.participant_type,
                'participant_id': p.participant_id,
                **info,
            })
        elif p.participant_name:
            # Use stored agent info
            enriched.append({
                'participant_type': p.participant_type,
                'participant_id': p.participant_id,
                'name': p.participant_name,
                'avatar': p.participant_avatar or '',
                'color': p.participant_color or '#4080ff',
            })
        else:
            # Fall back to DB lookup
            info = _participant_display_info(p.participant_type, p.participant_id)
            enriched.append({
                'participant_type': p.participant_type,
                'participant_id': p.participant_id,
                **info,
            })
    return enriched


class ConversationService:
    """Conversation business logic."""

    def _conv_to_dict(self, conversation):
        """Serialize conversation with participants."""
        data = conversation.to_dict()
        data['participant_ids'] = [
            f"{p.participant_type}_{p.participant_id}"
            for p in conversation.participants
        ]
        data['participants_info'] = _enrich_participants(conversation.participants)
        return data

    def create_conversation(self, title, conv_type, owner_id, participant_ids, workspace_id=None, kb_domain='', kb_document_ids=None, services=None, project_id=None):
        """Create a new conversation with participants, optionally in a workspace."""
        conversation = conversation_repo.create(
            title=title,
            type=conv_type,
            owner_id=owner_id,
            workspace_id=workspace_id,
            kb_domain=kb_domain or None,
            kb_document_ids=kb_document_ids or None,
            services=services or None,
            project_id=project_id or None,
        )

        # Add owner as participant with display info
        info = _participant_display_info('user', owner_id)
        conversation_repo.add_participant(
            conversation_id=conversation.id,
            participant_type='user',
            participant_id=owner_id,
            participant_name=info['name'],
            participant_avatar=info['avatar'],
            participant_color=info['color'],
        )

        normalized_participant_ids = self._with_auto_moderator(participant_ids or [])

        # Add other participants (users or agents)
        for pid in normalized_participant_ids:
            if pid.startswith('agent_'):
                actual_id = pid.replace('agent_', '')
                agent = agent_repo.get_by_id(actual_id)
                if agent:
                    info = _participant_display_info('agent', actual_id)
                    conversation_repo.add_participant(
                        conversation_id=conversation.id,
                        participant_type='agent',
                        participant_id=actual_id,
                        participant_name=info['name'],
                        participant_avatar=info['avatar'],
                        participant_color=info['color'],
                    )
            else:
                info = _participant_display_info('user', pid)
                conversation_repo.add_participant(
                    conversation_id=conversation.id,
                    participant_type='user',
                    participant_id=pid,
                    participant_name=info['name'],
                    participant_avatar=info['avatar'],
                    participant_color=info['color'],
                )

        agent_participants = [
            p for p in conversation.participants
            if p.participant_type == 'agent'
        ]
        if agent_participants:
            error = self._create_agent_sandbox(conversation, agent_participants, owner_id, kb_domain=kb_domain)
            if error:
                conversation.delete()
                return None, error

        return self._conv_to_dict(conversation), None

    def _with_auto_moderator(self, participant_ids):
        agent_ids = []
        for pid in participant_ids:
            if pid.startswith('agent_'):
                agent_ids.append(pid.replace('agent_', ''))
        if len([aid for aid in agent_ids if aid != MODERATOR_AGENT_ID]) >= 2:
            if not Agent.query.get(MODERATOR_AGENT_ID):
                try:
                    from app.services.agent_service import agent_service
                    agent_service.seed_default_data()
                except Exception:
                    pass
            if not Agent.query.get(MODERATOR_AGENT_ID):
                return participant_ids
            moderator_pid = f'agent_{MODERATOR_AGENT_ID}'
            participant_ids = [pid for pid in participant_ids if pid != moderator_pid]
            participant_ids.append(moderator_pid)
        return participant_ids

    def _create_single_agent_sandbox(self, conversation, participant, user_id, kb_domain=''):
        return self._create_agent_sandbox(conversation, [participant], user_id, kb_domain=kb_domain)

    def _create_agent_sandbox(self, conversation, participants, user_id, kb_domain=''):
        import json as _json

        env_vars, error = settings_service.get_container_env_vars(user_id)
        if error:
            return error

        # Pass user's auth token so sandbox tools can call services on behalf of the user
        auth_header = request.headers.get("Authorization", "")
        if auth_header:
            env_vars["USER_AUTH_TOKEN"] = auth_header

        # Pass KB document IDs to sandbox so rag_search can auto-filter
        if conversation.kb_document_ids:
            env_vars['KB_DOCUMENT_IDS'] = _json.dumps(conversation.kb_document_ids)

        # ── [NEW] 服务 & 项目环境变量 ──────────────────────
        services_list = conversation.services or []
        env_vars["CONVERSATION_SERVICES"] = _json.dumps(services_list)
        env_vars["RD_PROJECT_ID"] = conversation.project_id or ""

        # ── [NEW] 用户信息 ─────────────────────────────────
        user = User.query.get(user_id)
        user_context = _build_user_context(user) if user else ""

        # ── [NEW] 项目上下文 ───────────────────────────────
        project_context = ""
        if 'rd' in services_list:
            if conversation.project_id:
                project_context = _build_project_context(conversation.project_id)
            else:
                project_context = _build_rd_base_context()

        # ── [NEW] 服务能力摘要 ─────────────────────────────
        services_summary = _build_services_summary(services_list) if services_list else ""

        # ── KB 上下文 ─────────────────────────────────────
        kb_context = ''
        effective_domain = kb_domain.strip() if kb_domain and kb_domain != 'all' else ''
        if kb_domain == 'all':
            effective_domain = ''
        if conversation.workspace_id or kb_domain:
            try:
                from app.models.workspace import Workspace
                workspace = Workspace.query.get(conversation.workspace_id) if conversation.workspace_id else None
                domain = effective_domain or (workspace.domain if workspace else '')
                if domain:
                    domain_names = {'rd': '智能研发', 'edu': '智慧教育', 'office': '智慧办公'}
                    domain_name = domain_names.get(domain, domain)
                    workspace_info = f'\n- 工作空间: {workspace.name} (id: {workspace.id})' if workspace else ''
                    kb_context = (
                        f'知识库上下文:\n'
                        f'- 当前领域: {domain_name} ({domain})'
                        f'{workspace_info}\n'
                        f'- 你可以使用 rag_search 工具检索知识库中的文档内容\n'
                        f'- 检索时建议使用 domain="{domain}" 参数过滤当前领域的文档\n'
                        f'- 如果用户问题涉及专业领域知识，优先检索知识库获取相关信息'
                    )
                elif kb_domain == 'all':
                    kb_context = (
                        f'知识库上下文:\n'
                        f'- 知识库范围: 全部领域\n'
                        f'- 你可以使用 rag_search 工具检索知识库中的文档内容\n'
                        f'- 检索时可以不限制 domain 参数，搜索所有领域的文档\n'
                        f'- 如果用户问题涉及专业领域知识，优先检索知识库获取相关信息'
                    )
            except Exception:
                pass

        agents_config = []
        for participant in participants:
            agent = Agent.query.get(participant.participant_id)
            if not agent:
                return 'Agent not found'

            workspace_name = _safe_workspace_name(agent.name)
            work_dir = f'/workspace/agents/{workspace_name}'
            system_prompt_parts = [agent.system_prompt or '']
            if participant.participant_id == MODERATOR_AGENT_ID:
                worker_infos = []
                for p in participants:
                    if p.participant_id == MODERATOR_AGENT_ID:
                        continue
                    worker_agent = Agent.query.get(p.participant_id)
                    if worker_agent:
                        worker_infos.append(
                            f'- agent_id: {worker_agent.id}; name: {worker_agent.name}; tags: {", ".join(worker_agent.capability_tags or [])}'
                        )
                system_prompt_parts.append(
                    '\n\n当前可分配 worker_agents:\n' + '\n'.join(worker_infos)
                    if worker_infos else '\n\n当前没有可分配 worker_agents。'
                )
            if agent.skill:
                system_prompt_parts.append(f'\n\n工作流程:\n{agent.skill}')
            # ── 按顺序注入上下文块 ─────────────────────────
            if user_context:
                system_prompt_parts.append(f'\n\n{user_context}')
            if project_context:
                system_prompt_parts.append(f'\n\n{project_context}')
            if kb_context:
                system_prompt_parts.append(f'\n\n{kb_context}')
            if services_summary:
                system_prompt_parts.append(f'\n\n{services_summary}')
            system_prompt_parts.append(f"""

文件产物要求:
- 如果任务需要生成页面、代码、文档或其它文件，必须实际写入 {work_dir}/ 下的文件。
- 不要只在回复中描述"已创建文件"；必须让文件真实存在于工作目录。
- 前端页面入口优先写入 {work_dir}/index.html，相关资源放入同目录的 css/、js/ 或 assets/。
- 回复正文只总结产物和使用方式，不要要求用户手动进入 Docker 容器。
- 如写入了可预览 HTML，请明确提到入口文件 index.html。
""")

            agents_config.append({
                'agent_id': agent.id,
                'role': agent.name,
                'workspace_name': workspace_name,
                'system_prompt': '\n'.join(part for part in system_prompt_parts if part),
                'adapter_name': agent.adapter_name or 'claude',
            })

        try:
            from app.sandbox import get_manager
            session = get_manager().create_session(
                conversation.id,
                agents_config,
                env_vars=env_vars,
            )
        except Exception as e:
            return f'创建沙箱容器失败：{e}'

        conversation.sandbox_session_id = session.session_id
        conversation.sandbox_container_id = session.container_id
        conversation.sandbox_host_port = session.host_port
        conversation.sandbox_status = 'running'
        conversation.last_active_at = beijing_now()
        db.session.commit()
        return None

    def get_user_conversations(self, user_id, workspace_id=None):
        """Get all conversations for a user with last message, optionally filtered by workspace."""
        conversations = conversation_repo.get_user_conversations(user_id, workspace_id=workspace_id)
        result = []
        for conv in conversations:
            conv_data = self._conv_to_dict(conv)
            last_msg = conv.messages.order_by(Message.created_at.desc()).first()
            if last_msg:
                conv_data['last_message'] = {
                    'id': last_msg.id,
                    'content': last_msg.content[:100] if last_msg.content else '',
                    'sender_type': last_msg.sender_type,
                    'sender_id': last_msg.sender_id,
                    'created_at': format_beijing(last_msg.created_at),
                }
            result.append(conv_data)
        return result, None

    def get_conversation_detail(self, conversation_id):
        """Get conversation detail."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        return self._conv_to_dict(conversation), None

    def update_conversation_kb(self, conversation_id, user_id, kb_domain=None, kb_document_ids=None):
        """Update KB settings for a conversation (can be called mid-conversation)."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'

        if kb_domain is not None:
            conversation.kb_domain = kb_domain if kb_domain else None
        if kb_document_ids is not None:
            conversation.kb_document_ids = kb_document_ids if kb_document_ids else None

        db.session.commit()

        # Push kb_document_ids update to sandbox container if running
        try:
            from app.sandbox import get_manager
            import json as _json
            import urllib.request as _urllib
            mgr = get_manager()
            session = mgr.get_session(conversation_id)
            if session and session.host_port:
                _payload = _json.dumps({
                    "kb_document_ids": conversation.kb_document_ids,
                }).encode("utf-8")
                _req = _urllib.request.Request(
                    f"http://localhost:{session.host_port}/api/config/kb",
                    data=_payload,
                    headers={"Content-Type": "application/json"},
                )
                try:
                    _urllib.request.urlopen(_req, timeout=5)
                except Exception:
                    pass  # Sandbox might not be ready yet, ignore
        except Exception:
            pass  # Sandbox not available, ignore

        return self._conv_to_dict(conversation), None

    def get_owned_conversation_or_error(self, conversation_id, user_id):
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        return conversation, None

    @staticmethod
    def resolve_sandbox_session_id(conversation):
        if not conversation:
            return None
        return conversation.sandbox_session_id or conversation.id

    def create_migration_result_message(
        self,
        conversation_id,
        summary_text,
        result_text=None,
        status='done',
    ):
        msg = Message(
            conversation_id=conversation_id,
            sender_type='agent',
            sender_id='system',
            content=summary_text,
            message_type='text',
            status=status,
            elements=[{
                'type': 'result',
                'content': result_text or summary_text,
                'status': status,
            }],
        )
        db.session.add(msg)
        db.session.commit()
        socketio.emit('conversation_message_created', _message_dict(msg), room=conversation_id)
        return msg

    def set_conversation_favorite(self, conversation_id, user_id, is_favorite):
        """Update conversation favorite state."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'

        if isinstance(is_favorite, str):
            favorite_value = is_favorite.strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            favorite_value = bool(is_favorite)

        updated = conversation_repo.update(
            conversation,
            is_favorite=favorite_value,
        )
        return self._conv_to_dict(updated), None

    def delete_conversation(self, conversation_id, user_id):
        """Delete a conversation (owner only)."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        if conversation.sandbox_session_id:
            try:
                from app.sandbox import get_manager
                get_manager().destroy_session(conversation.sandbox_session_id)
            except Exception:
                pass
        AgentRun.query.filter_by(conversation_id=conversation.id).delete(
            synchronize_session=False
        )
        db.session.delete(conversation)
        db.session.commit()
        return {'deleted': True}, None

    def stop_agent(self, conversation_id, agent_id, user_id):
        """Stop a single agent run in a formal conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        if not conversation.sandbox_session_id:
            return None, 'Conversation has no sandbox session'

        try:
            from app.sandbox import get_manager
            result = get_manager().stop_agent(conversation.sandbox_session_id, agent_id)
        except Exception as e:
            return None, str(e)

        from app.services.sandbox_event_bridge import sandbox_event_bridge
        sandbox_event_bridge.mark_agent_stopped(conversation.id, agent_id)
        return result, None

    def _get_conversation_agent(self, conversation, agent_id=None):
        agents = [p for p in conversation.participants if p.participant_type == 'agent']
        if agent_id:
            return next((p for p in agents if p.participant_id == agent_id), None)
        return agents[0] if len(agents) == 1 else None

    def list_attachments(self, conversation_id, user_id, agent_id=None):
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        agent = self._get_conversation_agent(conversation, agent_id)
        if not agent:
            return None, '阶段 1 仅支持单 Agent 会话附件'
        if not conversation.sandbox_session_id:
            return None, 'Conversation has no sandbox session'

        workspace_name = _safe_workspace_name(agent.participant_name or agent.participant_id)
        root = f'/workspace/agents/{workspace_name}/userInput'
        try:
            from app.sandbox import get_manager
            result = get_manager().get_file_tree(conversation.sandbox_session_id, root=root)
        except Exception as e:
            return None, str(e)

        files = []

        def walk(node):
            if not node:
                return
            if node.get('type') == 'file':
                files.append({
                    'name': node.get('name'),
                    'path': node.get('path'),
                    'size': node.get('size'),
                    'agent_id': agent.participant_id,
                })
            for child in node.get('children') or []:
                walk(child)

        if result and result.get('error') and 'Path not found' in result.get('error', ''):
            result = {}
        if result and result.get('error'):
            return None, result.get('error')
        if result and result.get('tree'):
            walk(result.get('tree'))
        return {
            'agent_id': agent.participant_id,
            'agent_name': agent.participant_name,
            'root': root,
            'files': files,
        }, None

    def upload_attachment(self, conversation_id, user_id, file, agent_id=None):
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        if not file or not file.filename:
            return None, 'No file selected'
        agent = self._get_conversation_agent(conversation, agent_id)
        if not agent:
            return None, '阶段 1 仅支持单 Agent 会话附件'
        if not conversation.sandbox_session_id:
            return None, 'Conversation has no sandbox session'

        filename = _safe_upload_filename(file.filename) or 'upload.bin'
        workspace_name = _safe_workspace_name(agent.participant_name or agent.participant_id)
        path = f'/workspace/agents/{workspace_name}/userInput/{filename}'
        content = file.read()
        try:
            from app.sandbox import get_manager
            result = get_manager().upload_agent_file(
                conversation.sandbox_session_id,
                agent.participant_id,
                path,
                filename,
                content,
                file.mimetype or 'application/octet-stream',
            )
        except Exception as e:
            return None, str(e)
        if result.get('error'):
            return None, result.get('error')
        return {
            'name': filename,
            'path': result.get('path', path),
            'size': result.get('size', len(content)),
            'agent_id': agent.participant_id,
            'agent_name': agent.participant_name,
        }, None

    def delete_attachment(self, conversation_id, user_id, path, agent_id=None):
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'
        if not path:
            return None, 'path required'
        agent = self._get_conversation_agent(conversation, agent_id)
        if not agent:
            return None, '阶段 1 仅支持单 Agent 会话附件'
        if not conversation.sandbox_session_id:
            return None, 'Conversation has no sandbox session'

        try:
            from app.sandbox import get_manager
            result = get_manager().delete_agent_file(
                conversation.sandbox_session_id,
                agent.participant_id,
                path,
            )
        except Exception as e:
            return None, str(e)
        if result.get('error'):
            return None, result.get('error')
        return {'deleted': True, 'path': path}, None

    def add_participant(self, conversation_id, participant_type, participant_id, user_id):
        """Add a participant to conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'

        info = _participant_display_info(participant_type, participant_id)
        conversation_repo.add_participant(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            participant_name=info['name'],
            participant_avatar=info['avatar'],
            participant_color=info['color'],
        )
        return {'added': True}, None

    def remove_participant(self, conversation_id, participant_type, participant_id, user_id):
        """Remove a participant from conversation."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None, 'Conversation not found'
        if conversation.owner_id != user_id:
            return None, 'Permission denied'

        conversation_repo.remove_participant(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id
        )
        return {'removed': True}, None


conversation_service = ConversationService()
