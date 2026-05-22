from app.models import BaseModel, db


class Message(BaseModel):
    """Message model - stores chat messages."""
    __tablename__ = 'messages'

    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'),
                                nullable=False, index=True)
    sender_type = db.Column(db.Enum('user', 'agent', name='sender_type'),
                            nullable=False)
    sender_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.Text, nullable=False, default='')
    message_type = db.Column(
        db.Enum('text', 'code', 'image', 'file', 'artifact_card', 'diff_card',
                name='message_type'),
        nullable=False, default='text'
    )
    artifact_id = db.Column(db.String(36), db.ForeignKey('artifacts.id'),
                            nullable=True)
    parent_message_id = db.Column(db.String(36), db.ForeignKey('messages.id'),
                                  nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    elements = db.Column(db.JSON, nullable=True)
    """Structured content array: [{"type": "text|code|image|table|file", "data": {...}}]"""

    # Relationships
    artifact = db.relationship('Artifact', backref='message', lazy='joined',
                               foreign_keys='Message.artifact_id')
    # Self-referential: parent_message is the message this one replies to
    parent_message = db.relationship(
        'Message',
        remote_side='Message.id',
        foreign_keys='Message.parent_message_id',
        lazy='select',
        backref=db.backref('replies', lazy='select', order_by='Message.created_at')
    )
