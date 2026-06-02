from marshmallow import Schema, fields, validate


class CreateAgentSchema(Schema):
    """Create agent request schema."""
    name = fields.String(required=True, validate=validate.Length(max=100))
    capability_tags = fields.List(fields.String(), load_default=list)
    agent_type = fields.String(validate=validate.OneOf(['external', 'custom']), load_default='custom')
    adapter_name = fields.String(validate=validate.OneOf(['claude', 'codex', 'opencode']), load_default='claude')
    config = fields.Dict(load_default=dict)
    system_prompt = fields.String(load_default='')
    skill = fields.String(load_default='')
    avatar_color = fields.String(load_default='')
    avatar_url = fields.String(load_default='')
    class_id = fields.String(load_default=None, allow_none=True)
    is_public = fields.Boolean(load_default=False)
    tool_ids = fields.List(fields.String(), load_default=list)
    capability_bindings = fields.List(fields.Dict(), load_default=list)


class AgentResponseSchema(Schema):
    """Agent response schema."""
    id = fields.String()
    name = fields.String()
    avatar_url = fields.String()
    avatar_color = fields.String()
    capability_tags = fields.List(fields.String())
    agent_type = fields.String()
    adapter_name = fields.String()
    config = fields.Dict()
    system_prompt = fields.String()
    skill = fields.String()
    class_id = fields.String(allow_none=True)
    created_by = fields.String(allow_none=True)
    user_id = fields.String(allow_none=True)
    is_public = fields.Boolean()
    tool_ids = fields.List(fields.String())
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class CategoryResponseSchema(Schema):
    """Category response schema."""
    id = fields.String()
    name = fields.String()
    icon = fields.String()
    color = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
