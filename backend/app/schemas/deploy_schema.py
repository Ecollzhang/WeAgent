from marshmallow import Schema, fields


class CreateDeploySchema(Schema):
    conversation_id = fields.String(required=True)
    artifact_id = fields.String(allow_none=True)
    source_type = fields.String(load_default='webpage')
