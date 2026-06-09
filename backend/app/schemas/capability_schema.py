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
    category_id = fields.String(load_default=None, allow_none=True)
    category_slug = fields.String(load_default=None, allow_none=True)
    assets = fields.List(fields.Dict(), load_default=list)


class ImportMarkdownSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    markdown = fields.String(required=True)
    source_ref = fields.String(load_default="markdown")
    category_id = fields.String(load_default=None, allow_none=True)
    category_slug = fields.String(load_default=None, allow_none=True)


class ImportNpxManifestSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    manifest = fields.Dict(required=True)
    source_ref = fields.String(load_default="")
    category_id = fields.String(load_default=None, allow_none=True)
    category_slug = fields.String(load_default=None, allow_none=True)


class ImportPreviewSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    source_type = fields.String(
        required=True,
        validate=validate.OneOf(["markdown", "upload", "repo", "npx"]),
    )
    source_ref = fields.String(load_default="")
    markdown = fields.String(load_default=None, allow_none=True)
    repo_path = fields.String(load_default=None, allow_none=True)
    upload_name = fields.String(load_default=None, allow_none=True)
    upload_base64 = fields.String(load_default=None, allow_none=True)


class ImportConfirmSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    import_job_id = fields.String(required=True)
    selected_entries = fields.List(fields.String(), load_default=list)
    category_id = fields.String(load_default=None, allow_none=True)
    category_slug = fields.String(load_default=None, allow_none=True)
    override_confirmed = fields.Boolean(load_default=False)
    override_reason = fields.String(load_default="")


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
    assets = fields.List(fields.Dict(), load_default=list)


class DraftPublishSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    version = fields.String(load_default=None, allow_none=True)
    override_confirmed = fields.Boolean(load_default=False)
    override_reason = fields.String(load_default="")


class DraftForkSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None, allow_none=True)


class CallSyncSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    records = fields.List(fields.Dict(), required=True)


class DraftSyncSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    records = fields.List(fields.Dict(), required=True)


class CreateToolProviderConfigSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    profile_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=120),
    )
    provider_type = fields.String(
        required=True,
        validate=validate.OneOf(["mcp", "http", "model", "database"]),
    )
    config = fields.Dict(load_default=dict)
    secret_refs = fields.List(fields.String(), load_default=list)


class UpdateToolProviderConfigSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    profile_name = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(min=1, max=120),
    )
    provider_type = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["mcp", "http", "model", "database"]),
    )
    config = fields.Dict(load_default=None, allow_none=True)
    secret_refs = fields.List(fields.String(), load_default=None, allow_none=True)
