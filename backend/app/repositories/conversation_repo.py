from app.repositories.base_repo import BaseRepository
from app.models.conversation import Conversation, ConversationParticipant


class ConversationRepository(BaseRepository):
    """Conversation repository."""

    def __init__(self):
        super().__init__(Conversation)

    def get_user_conversations(self, user_id):
        """Get all conversations for a user."""
        participant_ids = ConversationParticipant.query.filter_by(
            participant_type='user',
            participant_id=user_id
        ).with_entities(ConversationParticipant.conversation_id).all()

        conversation_ids = [p[0] for p in participant_ids]
        if not conversation_ids:
            return []

        conversations = Conversation.query.filter(
            Conversation.id.in_(conversation_ids)
        ).order_by(Conversation.updated_at.desc()).all()

        return conversations

    def get_conversation_participants(self, conversation_id):
        """Get all participants of a conversation."""
        return ConversationParticipant.query.filter_by(
            conversation_id=conversation_id
        ).all()

    def add_participant(self, conversation_id, participant_type, participant_id,
                        participant_name='', participant_avatar='', participant_color=''):
        """Add a participant to a conversation."""
        participant = ConversationParticipant(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            participant_name=participant_name,
            participant_avatar=participant_avatar,
            participant_color=participant_color,
        )
        participant.save()
        return participant

    def remove_participant(self, conversation_id, participant_type, participant_id):
        """Remove a participant from a conversation."""
        participant = ConversationParticipant.query.filter_by(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id
        ).first()
        if participant:
            participant.delete()


conversation_repo = ConversationRepository()
