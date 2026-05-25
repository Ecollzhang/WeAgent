from app.repositories.base_repo import BaseRepository
from app.models.message import Message


class MessageRepository(BaseRepository):
    """Message repository."""

    def __init__(self):
        super().__init__(Message)

    def get_conversation_messages(self, conversation_id, page=1, per_page=50):
        """Get paginated messages for a conversation."""
        return Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(
            Message.created_at.asc(),
            Message.sender_type.desc(),
            Message.id.asc(),
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )

    def get_pinned_messages(self, conversation_id):
        """Get pinned messages for a conversation."""
        return Message.query.filter_by(
            conversation_id=conversation_id,
            is_pinned=True
        ).order_by(
            Message.created_at.asc(),
            Message.sender_type.desc(),
            Message.id.asc(),
        ).all()

    def toggle_pin(self, message_id):
        """Toggle pin status of a message."""
        message = self.get_by_id(message_id)
        if message:
            message.is_pinned = not message.is_pinned
            message.save()
        return message


message_repo = MessageRepository()
