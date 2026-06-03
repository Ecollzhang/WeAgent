from app.models.message import Message
from app.utils.timezone import format_beijing, beijing_now
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_run import AgentRun
from app import db
from app.repositories.conversation_repo import conversation_repo
from app.repositories.agent_repo import agent_repo
from app.repositories.message_repo import message_repo
from app.services.settings_service import settings_service
MODERATOR_AGENT_ID = 'moderator'


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

    def create_conversation(self, title, conv_type, owner_id, participant_ids):
        """Create a new conversation with participants."""
        conversation = conversation_repo.create(
            title=title,
            type=conv_type,
            owner_id=owner_id
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
            error = self._create_agent_sandbox(conversation, agent_participants, owner_id)
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

    def _create_single_agent_sandbox(self, conversation, participant, user_id):
        return self._create_agent_sandbox(conversation, [participant], user_id)

    def _create_agent_sandbox(self, conversation, participants, user_id):
        env_vars, error = settings_service.get_container_env_vars(user_id)
        if error:
            return error

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
            system_prompt_parts.append(f"""

文件产物要求:
- 如果任务需要生成页面、代码、文档或其它文件，必须实际写入 {work_dir}/ 下的文件。
- 不要只在回复中描述“已创建文件”；必须让文件真实存在于工作目录。
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

    def get_user_conversations(self, user_id):
        """Get all conversations for a user with last message."""
        conversations = conversation_repo.get_user_conversations(user_id)
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
