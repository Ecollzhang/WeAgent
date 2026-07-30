import hashlib
import os
import re
import uuid
from datetime import timedelta

from flask import current_app
import requests

from app.models.conversation import Conversation
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


def _trusted_education_runtime_env(agent_configs, kb_domain=''):
    """Extract one opaque Education grant without exposing it to Agent prompts."""
    if kb_domain != 'edu' or not isinstance(agent_configs, dict):
        return {}
    grants = set()
    for config in agent_configs.values():
        if not isinstance(config, dict):
            continue
        context = config.get('education_tool_context')
        if not isinstance(context, dict):
            continue
        token = str(context.get('run_grant') or '').strip()
        if token:
            grants.add(token)
    if not grants:
        return {}
    if len(grants) != 1:
        raise ValueError('conflicting Education run grants')
    token = grants.pop()
    import re
    if not re.fullmatch(r'[A-Za-z0-9._~-]{20,256}', token):
        raise ValueError('invalid Education run grant')
    import os
    return {
        'EDUCATION_RUN_GRANT': token,
        'EDUCATION_SERVICE_URL': os.getenv(
            'EDUCATION_SERVICE_URL',
            'http://host.docker.internal:5102',
        ).rstrip('/'),
    }


def _validate_education_runtime_grant(token, actor_user_id):
    """Confirm the opaque runtime grant belongs to the authenticated actor."""
    base_url = str(
        current_app.config.get(
            'EDUCATION_RUNTIME_VALIDATION_URL',
            'http://127.0.0.1:5102',
        )
    ).rstrip('/')
    try:
        response = requests.post(
            f'{base_url}/api/edu/tool-grants/verify-runtime',
            headers={'X-Education-Run-Grant': str(token or '')},
            json={'actor_user_id': str(actor_user_id or '')},
            timeout=(2, 5),
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        return False
    return response.status_code == 200 and payload.get('valid') is True


def _trusted_rag_scope(conversation, user_id, kb_domain=''):
    """Build a server-issued RAG scope; model/tool arguments cannot widen it."""
    allowed_domains = {'rd', 'edu', 'office'}
    scope = {
        'RAG_SCOPE_USER_ID': str(user_id),
        'RAG_SCOPE_DOMAIN': kb_domain if kb_domain in allowed_domains else 'rd',
    }
    if conversation.workspace_id:
        from app.models.workspace import Workspace

        workspace = Workspace.query.filter_by(
            id=conversation.workspace_id,
            user_id=user_id,
        ).first()
        if workspace and workspace.domain in allowed_domains:
            scope['RAG_SCOPE_DOMAIN'] = workspace.domain
            scope['RAG_SCOPE_WORKSPACE_ID'] = workspace.id
    return scope


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
        data.pop('sandbox_snapshot_path', None)
        data.pop('sandbox_snapshot_sha256', None)
        data.pop('sandbox_server_fallback', None)
        data.pop('sandbox_agent_adapters', None)
        data['sandbox_runtime'] = {
            'status': conversation.sandbox_status,
            'generation': conversation.sandbox_generation or 1,
            'expires_at': format_beijing(conversation.sandbox_expires_at),
            'snapshot_available': bool(conversation.sandbox_snapshot_path),
            'snapshot_at': format_beijing(conversation.sandbox_snapshot_at),
        }
        data['participant_ids'] = [
            f"{p.participant_type}_{p.participant_id}"
            for p in conversation.participants
        ]
        data['participants_info'] = _enrich_participants(conversation.participants)
        return data

    def create_conversation(self, title, conv_type, owner_id, participant_ids,
                            workspace_id=None, kb_domain='', agent_configs=None):
        """Create a new conversation with participants, optionally in a workspace."""
        conversation = conversation_repo.create(
            title=title,
            type=conv_type,
            owner_id=owner_id,
            workspace_id=workspace_id,
        )
        conversation.kb_domain = (
            str(kb_domain or '').strip()
            if str(kb_domain or '').strip() in {'rd', 'edu', 'office'}
            else ''
        )
        allowed_adapters = {'claude', 'codex', 'opencode'}
        conversation.sandbox_agent_adapters = {
            str(agent_id): adapter
            for agent_id, config in (agent_configs or {}).items()
            if isinstance(config, dict)
            for adapter in [str(config.get('adapter_name') or '').strip()]
            if adapter in allowed_adapters
        }
        db.session.commit()

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
            error = self._create_agent_sandbox(
                conversation,
                agent_participants,
                owner_id,
                kb_domain=kb_domain,
                agent_configs=agent_configs,
            )
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

    def _create_agent_sandbox(
        self,
        conversation,
        participants,
        user_id,
        kb_domain='',
        agent_configs=None,
        allow_server_fallback=False,
        rehydrating=False,
    ):
        try:
            education_runtime_env = _trusted_education_runtime_env(
                agent_configs,
                kb_domain=kb_domain,
            )
        except ValueError as exc:
            return str(exc)
        if education_runtime_env:
            valid = _validate_education_runtime_grant(
                education_runtime_env['EDUCATION_RUN_GRANT'],
                user_id,
            )
            if not valid:
                return 'Education runtime authorization is invalid'
            allow_server_fallback = True
            conversation.sandbox_server_fallback = True
        elif not rehydrating:
            conversation.sandbox_server_fallback = False
        env_vars, error = settings_service.get_container_env_vars(
            user_id,
            allow_server_fallback=bool(allow_server_fallback),
        )
        if error:
            return error
        env_vars = dict(env_vars or {})
        rag_scope = _trusted_rag_scope(conversation, user_id, kb_domain)
        env_vars.update(rag_scope)
        env_vars.update(education_runtime_env)

        # Build KB context from workspace domain (or explicit kb_domain override)
        kb_context = ''
        effective_domain = rag_scope['RAG_SCOPE_DOMAIN']
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

        allowed_adapters = {'claude', 'codex', 'opencode'}
        config_map = agent_configs if isinstance(agent_configs, dict) else {}
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
            if kb_context:
                system_prompt_parts.append(f'\n\n{kb_context}')
            system_prompt_parts.append(f"""

文件产物要求:
- 如果任务需要生成页面、代码、文档或其它文件，必须实际写入 {work_dir}/ 下的文件。
- 不要只在回复中描述“已创建文件”；必须让文件真实存在于工作目录。
- 前端页面入口优先写入 {work_dir}/index.html，相关资源放入同目录的 css/、js/ 或 assets/。
- 回复正文只总结产物和使用方式，不要要求用户手动进入 Docker 容器。
- 如写入了可预览 HTML，请明确提到入口文件 index.html。
""")

            override = config_map.get(str(agent.id))
            override_adapter = (
                str(override.get('adapter_name') or '').strip()
                if isinstance(override, dict) else ''
            )
            adapter_name = (
                override_adapter
                if override_adapter in allowed_adapters
                else (agent.adapter_name or 'claude')
            )
            agents_config.append({
                'agent_id': agent.id,
                'role': agent.name,
                'workspace_name': workspace_name,
                'system_prompt': '\n'.join(part for part in system_prompt_parts if part),
                'adapter_name': adapter_name,
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
        conversation.sandbox_generation = conversation.sandbox_generation or 1
        conversation.sandbox_expires_at = (
            beijing_now() + timedelta(seconds=self._sandbox_ttl_seconds())
        )
        conversation.stopped_at = None
        db.session.commit()
        return None

    @staticmethod
    def _sandbox_ttl_seconds():
        return max(300, int(current_app.config.get('SANDBOX_TTL_SECONDS', 72 * 3600)))

    @staticmethod
    def _safe_snapshot_segment(value):
        return re.sub(r'[^A-Za-z0-9._-]', '_', str(value or 'unknown'))[:100]

    def _snapshot_absolute_path(self, conversation, relative_path=None):
        upload_root = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        relative = relative_path or os.path.join(
            'sandbox_snapshots',
            self._safe_snapshot_segment(conversation.owner_id),
            self._safe_snapshot_segment(conversation.id),
            f'generation-{int(conversation.sandbox_generation or 1)}.zip',
        )
        absolute = os.path.abspath(os.path.join(upload_root, relative))
        if absolute != upload_root and not absolute.startswith(upload_root + os.sep):
            raise ValueError('Invalid sandbox snapshot path')
        return upload_root, relative.replace('\\', '/'), absolute

    def snapshot_sandbox(self, conversation, manager=None):
        """Persist the visible workspace outside Docker before it can expire."""
        if not conversation or not conversation.sandbox_session_id:
            return {'status': 'skipped', 'reason': 'no sandbox session'}
        if manager is None:
            from app.sandbox import get_manager
            manager = get_manager()
        archive_bytes, _, _ = manager.export_zip(
            conversation.sandbox_session_id,
            '/workspace',
        )
        max_bytes = int(
            current_app.config.get('SANDBOX_SNAPSHOT_MAX_BYTES', 50 * 1024 * 1024)
        )
        if len(archive_bytes) > max_bytes:
            raise ValueError('Sandbox snapshot exceeds the configured size limit')

        _, relative, absolute = self._snapshot_absolute_path(conversation)
        os.makedirs(os.path.dirname(absolute), exist_ok=True)
        temporary = f'{absolute}.tmp-{uuid.uuid4().hex}'
        try:
            with open(temporary, 'wb') as stream:
                stream.write(archive_bytes)
            os.replace(temporary, absolute)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

        conversation.sandbox_snapshot_path = relative
        conversation.sandbox_snapshot_sha256 = hashlib.sha256(archive_bytes).hexdigest()
        conversation.sandbox_snapshot_size = len(archive_bytes)
        conversation.sandbox_snapshot_at = beijing_now()
        db.session.commit()
        return {
            'status': 'snapshotted',
            'runtime_generation': conversation.sandbox_generation or 1,
            'size': len(archive_bytes),
            'sha256': conversation.sandbox_snapshot_sha256,
        }

    def _restore_sandbox_snapshot(self, conversation, manager):
        if not conversation.sandbox_snapshot_path:
            return {'status': 'skipped', 'restored_files': 0}
        _, _, absolute = self._snapshot_absolute_path(
            conversation,
            conversation.sandbox_snapshot_path,
        )
        if not os.path.isfile(absolute):
            raise FileNotFoundError('Durable sandbox snapshot is missing')
        with open(absolute, 'rb') as stream:
            archive_bytes = stream.read()
        digest = hashlib.sha256(archive_bytes).hexdigest()
        if digest != conversation.sandbox_snapshot_sha256:
            raise ValueError('Durable sandbox snapshot integrity check failed')
        return manager.restore_zip(conversation.sandbox_session_id, archive_bytes)

    def ensure_sandbox_runtime(self, conversation, user_id, manager=None):
        """Return a live runtime, rehydrating a new generation when required."""
        if manager is None:
            from app.sandbox import get_manager
            manager = get_manager()
        session = (
            manager.get_session(conversation.sandbox_session_id)
            if conversation.sandbox_session_id
            else None
        )
        if session and getattr(session, '_check_alive', lambda: True)():
            conversation.sandbox_status = 'running'
            conversation.last_active_at = beijing_now()
            conversation.sandbox_expires_at = (
                beijing_now() + timedelta(seconds=self._sandbox_ttl_seconds())
            )
            db.session.commit()
            return {
                'rehydrated': False,
                'runtime_generation': conversation.sandbox_generation or 1,
            }, None

        if conversation.sandbox_session_id:
            manager.destroy_session(conversation.sandbox_session_id)
        previous_generation = int(conversation.sandbox_generation or 1)
        participants = [
            item for item in conversation.participants
            if item.participant_type == 'agent'
        ]
        saved_adapters = {
            str(agent_id): {'adapter_name': adapter}
            for agent_id, adapter in (
                conversation.sandbox_agent_adapters or {}
            ).items()
        }
        error = self._create_agent_sandbox(
            conversation,
            participants,
            user_id,
            kb_domain=conversation.kb_domain or '',
            agent_configs=saved_adapters,
            allow_server_fallback=bool(
                conversation.sandbox_server_fallback
            ),
            rehydrating=True,
        )
        if error:
            conversation.sandbox_status = 'error'
            db.session.commit()
            return None, error
        conversation.sandbox_generation = previous_generation + 1
        try:
            restored = self._restore_sandbox_snapshot(conversation, manager)
        except Exception as exc:
            manager.destroy_session(conversation.sandbox_session_id)
            conversation.sandbox_status = 'error'
            conversation.stopped_at = beijing_now()
            db.session.commit()
            return None, f'恢复持久工作区失败：{exc}'
        conversation.sandbox_status = 'running'
        conversation.stopped_at = None
        conversation.last_active_at = beijing_now()
        conversation.sandbox_expires_at = (
            beijing_now() + timedelta(seconds=self._sandbox_ttl_seconds())
        )
        db.session.commit()
        return {
            'rehydrated': True,
            'runtime_generation': conversation.sandbox_generation,
            'restored_files': restored.get('restored_files', 0),
        }, None

    def expire_idle_sandboxes(self, now=None, manager=None, owner_id=None):
        """Snapshot and stop expired runtimes without deleting durable chat data."""
        now = now or beijing_now()
        uninitialized = Conversation.query.filter(
            Conversation.sandbox_status == 'running',
            Conversation.sandbox_expires_at.is_(None),
        )
        if owner_id:
            uninitialized = uninitialized.filter(Conversation.owner_id == owner_id)
        for conversation in uninitialized.all():
            anchor = conversation.last_active_at or now
            conversation.sandbox_expires_at = (
                anchor + timedelta(seconds=self._sandbox_ttl_seconds())
            )
        db.session.commit()
        query = Conversation.query.filter(
            Conversation.sandbox_status == 'running',
            Conversation.sandbox_expires_at.isnot(None),
            Conversation.sandbox_expires_at <= now,
        )
        if owner_id:
            query = query.filter(Conversation.owner_id == owner_id)
        if manager is None:
            from app.sandbox import get_manager
            manager = get_manager()
        stopped = 0
        errors = []
        for conversation in query.all():
            try:
                self.snapshot_sandbox(conversation, manager=manager)
                manager.destroy_session(conversation.sandbox_session_id)
                conversation.sandbox_status = 'stopped'
                conversation.sandbox_container_id = None
                conversation.sandbox_host_port = None
                conversation.stopped_at = now
                db.session.commit()
                stopped += 1
            except Exception as exc:
                db.session.rollback()
                errors.append({'conversation_id': conversation.id, 'error': str(exc)})
        return {'stopped': stopped, 'errors': errors}

    def get_user_conversations(self, user_id, workspace_id=None):
        """Get all conversations for a user with last message, optionally filtered by workspace."""
        try:
            self.expire_idle_sandboxes(owner_id=user_id)
        except Exception:
            db.session.rollback()
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

    def get_conversation_detail(self, conversation_id, user_id):
        """Get conversation detail."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation or not self.user_can_access(conversation, user_id):
            return None, 'Conversation not found'
        return self._conv_to_dict(conversation), None

    @staticmethod
    def user_can_access(conversation, user_id):
        """Return whether a user is an explicit participant of a conversation."""
        if not conversation or not user_id:
            return False
        if conversation.owner_id == user_id:
            return True
        return any(
            participant.participant_type == 'user'
            and participant.participant_id == user_id
            for participant in conversation.participants
        )

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

    def runtime_preflight(self, conversation_id, user_id, required_tools):
        conversation, error = self.get_owned_conversation_or_error(
            conversation_id,
            user_id,
        )
        if error:
            return None, error
        required = sorted({
            str(item or '').strip()
            for item in (required_tools or [])
            if str(item or '').strip()
        })
        _, error = self.ensure_sandbox_runtime(conversation, user_id)
        if error:
            return None, error
        try:
            from app.sandbox import get_manager
            result = get_manager().preflight_tools(
                conversation.sandbox_session_id,
                required,
            )
        except Exception as exc:
            return None, str(exc)
        result['runtime_generation'] = conversation.sandbox_generation or 1
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
