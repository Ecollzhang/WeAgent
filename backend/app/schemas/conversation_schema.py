from marshmallow import Schema, fields, validate


class CreateConversationSchema(Schema):
    """Create conversation request schema."""
    title = fields.String(required=True, validate=validate.Length(max=200))
    type = fields.String(required=True, validate=validate.OneOf(['single', 'group']))
    participant_ids = fields.List(fields.String(), required=True)
    workspace_id = fields.String(required=False, allow_none=True)
    kb_domain = fields.String(required=False, allow_none=True, validate=validate.OneOf(['', 'all', 'rd', 'edu', 'office']))


class ConversationResponseSchema(Schema):
    """Conversation response schema."""
    id = fields.String()
    title = fields.String()
    type = fields.String()
    owner_id = fields.String()
    is_favorite = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    participants = fields.List(fields.Nested(lambda: ParticipantSchema()))
    last_message = fields.Nested(lambda: MessageSummarySchema(), allow_none=True)


class ParticipantSchema(Schema):
    """Participant schema."""
    id = fields.String()
    conversation_id = fields.String()
    participant_type = fields.String()
    participant_id = fields.String()
    joined_at = fields.DateTime()


class MessageSummarySchema(Schema):
    """Minimal message schema for conversation list."""
    id = fields.String()
    content = fields.String()
    sender_type = fields.String()
    sender_id = fields.String()
    created_at = fields.DateTime()
