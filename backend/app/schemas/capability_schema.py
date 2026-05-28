from marshmallow import EXCLUDE, Schema, fields, validate


class PermissionDeclarationSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    required = fields.List(fields.String(), load_default=list)
    optional = fields.List(fields.String(), load_default=list)


class CreateSkillSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    markdown = fields.String(required=True)
    description = fields.String(load_default="")
    permissions = fields.Nested(PermissionDeclarationSchema, load_default=dict)
    meta = fields.Dict(load_default=dict)
    source_ref = fields.String(load_default="manual")


class ImportMarkdownSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    markdown = fields.String(required=True)
    source_ref = fields.String(load_default="markdown")


class ImportNpxManifestSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    manifest = fields.Dict(required=True)
    source_ref = fields.String(load_default="")


class BindCapabilitySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    capability_version_id = fields.String(required=True)
    granted_permissions = fields.List(fields.String(), load_default=list)
    version_policy = fields.String(
        validate=validate.OneOf(["pinned", "follow_latest"]),
        load_default="pinned",
    )
    enabled = fields.Boolean(load_default=True)


class UpdateCapabilityBindingSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    capability_version_id = fields.String(load_default=None, allow_none=True)
    granted_permissions = fields.List(fields.String(), load_default=None, allow_none=True)
    version_policy = fields.String(
        validate=validate.OneOf(["pinned", "follow_latest"]),
        load_default=None,
        allow_none=True,
    )
    enabled = fields.Boolean(load_default=None, allow_none=True)


class CreateCapabilityVersionSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    content = fields.String(load_default="")
    manifest = fields.Dict(load_default=dict)
    permissions = fields.Nested(PermissionDeclarationSchema, load_default=dict)
    meta = fields.Dict(load_default=dict)
    version = fields.String(load_default=None, allow_none=True)


class DraftPublishSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    version = fields.String(load_default=None, allow_none=True)


class DraftForkSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None, allow_none=True)


class CallSyncSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    records = fields.List(fields.Dict(), required=True)
