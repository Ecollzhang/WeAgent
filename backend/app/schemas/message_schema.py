from marshmallow import Schema, fields, validate


class SendMessageSchema(Schema):
    """Send message request schema."""
    conversation_id = fields.String(required=True)
    content = fields.String(required=True)
    message_type = fields.String(validate=validate.OneOf(
        ['text', 'code', 'image', 'file', 'artifact_card', 'diff_card']
    ), load_default='text')
    parent_message_id = fields.String(allow_none=True)
    target_agent_ids = fields.List(fields.String(), load_default=list)


class MessageResponseSchema(Schema):
    """Message response schema."""
    id = fields.String()
    conversation_id = fields.String()
    sender_type = fields.String()
    sender_id = fields.String()
    content = fields.String()
    message_type = fields.String()
    artifact_id = fields.String(allow_none=True)
    parent_message_id = fields.String(allow_none=True)
    is_pinned = fields.Boolean()
    created_at = fields.DateTime()
    artifact = fields.Nested(lambda: ArtifactSummarySchema(), allow_none=True)


class ArtifactSummarySchema(Schema):
    """Minimal artifact schema for messages."""
    id = fields.String()
    artifact_type = fields.String()
    title = fields.String()
    language = fields.String()
