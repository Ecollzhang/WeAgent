from app.models.message import Message
from app.models.user import User
from app.models.agent import Agent
from app.repositories.conversation_repo import conversation_repo
from app.repositories.agent_repo import agent_repo
from app.repositories.message_repo import message_repo


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

        # Add other participants (users or agents)
        for pid in participant_ids:
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

        return self._conv_to_dict(conversation), None

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
                    'created_at': last_msg.created_at.isoformat(),
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
        conversation.delete()
        return {'deleted': True}, None

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
