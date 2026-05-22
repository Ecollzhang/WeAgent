from marshmallow import Schema, fields, validate


class CreateArtifactSchema(Schema):
    """Create artifact request schema."""
    message_id = fields.String(allow_none=True)
    artifact_type = fields.String(required=True, validate=validate.OneOf(
        ['code', 'webpage', 'document', 'ppt', 'diff']
    ))
    title = fields.String(required=True, validate=validate.Length(max=200))
    content = fields.String(load_default='')
    language = fields.String(load_default='')
    preview_url = fields.String(load_default='')
    deploy_url = fields.String(load_default='')


class ArtifactResponseSchema(Schema):
    """Artifact response schema."""
    id = fields.String()
    message_id = fields.String(allow_none=True)
    artifact_type = fields.String()
    title = fields.String()
    content = fields.String()
    language = fields.String()
    preview_url = fields.String()
    deploy_url = fields.String()
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
