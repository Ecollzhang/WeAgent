import base64

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.schemas.capability_schema import (
    BindCapabilitySchema,
    CallSyncSchema,
    CreateCapabilityVersionSchema,
    CreateSkillSchema,
    DraftSyncSchema,
    DraftForkSchema,
    DraftPublishSchema,
    ImportConfirmSchema,
    ImportMarkdownSchema,
    ImportNpxManifestSchema,
    ImportPreviewSchema,
    CreateToolProviderConfigSchema,
    UpdateToolProviderConfigSchema,
    UpdateCapabilityBindingSchema,
)
from app.services.capability_call_sync_service import capability_call_sync_service
from app.services.capability_draft_sync_service import capability_draft_sync_service
from app.services.capability_import_confirm_service import capability_import_confirm_service
from app.services.capability_import_preview_service import capability_import_preview_service
from app.services.capability_npx_import_sandbox import capability_npx_import_sandbox
from app.services.capability_service import capability_service
from app.services.tool_provider_config_service import tool_provider_config_service
from app.utils.response import error_response, success_response


capability_bp = Blueprint("capabilities", __name__)
agent_capability_bp = Blueprint("agent_capabilities", __name__)


def _load(schema_cls):
    try:
        return schema_cls().load(request.json or {}), None
    except ValidationError as exc:
        return None, str(exc.messages)


@capability_bp.route("", methods=["GET"])
@jwt_required()
def list_capabilities():
    user_id = get_jwt_identity()
    result, error = capability_service.list_capabilities(
        user_id=user_id,
        capability_type=request.args.get("type"),
        category_id=request.args.get("category_id"),
        domain=request.args.get("domain"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result)


@capability_bp.route("/skills", methods=["POST"])
@jwt_required()
def create_skill():
    user_id = get_jwt_identity()
    data, validation_error = _load(CreateSkillSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.create_skill(
        user_id=user_id,
        name=data["name"],
        markdown=data["markdown"],
        description=data.get("description", ""),
        permissions=data.get("permissions"),
        meta=data.get("meta"),
        source_ref=data.get("source_ref", "manual"),
        category_id=data.get("category_id"),
        category_slug=data.get("category_slug"),
        assets=data.get("assets"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capability created", code=201)


@capability_bp.route("/import/markdown", methods=["POST"])
@jwt_required()
def import_markdown_skill():
    user_id = get_jwt_identity()
    data, validation_error = _load(ImportMarkdownSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.import_skill_markdown(
        user_id=user_id,
        markdown=data["markdown"],
        source_ref=data.get("source_ref", "markdown"),
        category_id=data.get("category_id"),
        category_slug=data.get("category_slug"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capability imported", code=201)


@capability_bp.route("/import/npx-manifest", methods=["POST"])
@jwt_required()
def import_npx_manifest():
    user_id = get_jwt_identity()
    data, validation_error = _load(ImportNpxManifestSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.import_npx_manifest(
        user_id=user_id,
        manifest=data["manifest"],
        source_ref=data.get("source_ref", ""),
        category_id=data.get("category_id"),
        category_slug=data.get("category_slug"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capabilities imported", code=201)


@capability_bp.route("/import/mcp-manifest", methods=["POST"])
@jwt_required()
def import_mcp_manifest():
    user_id = get_jwt_identity()
    data, validation_error = _load(ImportNpxManifestSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.import_mcp_manifest(
        user_id=user_id,
        manifest=data["manifest"],
        source_ref=data.get("source_ref", ""),
        category_id=data.get("category_id"),
        category_slug=data.get("category_slug"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="MCP capabilities imported", code=201)


@capability_bp.route("/import/preview", methods=["POST"])
@jwt_required()
def preview_import():
    user_id = get_jwt_identity()
    data, validation_error = _load(ImportPreviewSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    source_type = data["source_type"]
    if source_type == "markdown":
        result, error = capability_import_preview_service.preview_markdown(
            user_id=user_id,
            markdown=data.get("markdown"),
            source_ref=data.get("source_ref") or "markdown",
        )
    elif source_type == "upload":
        try:
            zip_bytes = base64.b64decode(data.get("upload_base64") or "", validate=True)
        except (ValueError, TypeError):
            return error_response("Upload bundle must be base64 encoded", code=400)
        result, error = capability_import_preview_service.preview_zip_bundle(
            user_id=user_id,
            zip_bytes=zip_bytes,
            source_ref=data.get("source_ref") or data.get("upload_name") or "bundle.zip",
        )
    elif source_type == "repo":
        result, error = capability_import_preview_service.preview_repo_static(
            user_id=user_id,
            repo_path=data.get("repo_path"),
            source_ref=data.get("source_ref") or data.get("repo_path") or "repo",
        )
    elif source_type == "npx":
        result, error = capability_npx_import_sandbox.preview_npx(
            user_id=user_id,
            source_ref=data.get("source_ref") or "",
        )
    else:
        return error_response("Unsupported import source type", code=400)
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Import preview created", code=201)


@capability_bp.route("/import/confirm", methods=["POST"])
@jwt_required()
def confirm_import():
    user_id = get_jwt_identity()
    data, validation_error = _load(ImportConfirmSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_import_confirm_service.confirm_import_job(
        user_id=user_id,
        import_job_id=data["import_job_id"],
        selected_entries=data.get("selected_entries"),
        category_id=data.get("category_id"),
        category_slug=data.get("category_slug"),
        override_confirmed=data.get("override_confirmed", False),
        override_reason=data.get("override_reason", ""),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Import confirmed", code=201)


@capability_bp.route("/drafts", methods=["GET"])
@jwt_required()
def list_drafts():
    user_id = get_jwt_identity()
    result, error = capability_service.list_drafts(
        user_id=user_id,
        status=request.args.get("status"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result)


@capability_bp.route("/drafts/sync", methods=["POST"])
@jwt_required()
def sync_skill_drafts():
    user_id = get_jwt_identity()
    data, validation_error = _load(DraftSyncSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_draft_sync_service.sync_records(
        user_id=user_id,
        records=data["records"],
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Skill drafts synced", code=201)


@capability_bp.route("/drafts/<draft_id>/publish", methods=["POST"])
@jwt_required()
def publish_draft(draft_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(DraftPublishSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.publish_draft(
        user_id=user_id,
        draft_id=draft_id,
        version=data.get("version"),
        override_confirmed=data.get("override_confirmed", False),
        override_reason=data.get("override_reason", ""),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Draft published")


@capability_bp.route("/drafts/<draft_id>/fork", methods=["POST"])
@jwt_required()
def fork_draft(draft_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(DraftForkSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.fork_draft(
        user_id=user_id,
        draft_id=draft_id,
        name=data.get("name"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Draft forked", code=201)


@capability_bp.route("/calls/sync", methods=["POST"])
@jwt_required()
def sync_call_records():
    user_id = get_jwt_identity()
    data, validation_error = _load(CallSyncSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_call_sync_service.sync_records(
        user_id=user_id,
        records=data["records"],
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Call records synced", code=201)


@capability_bp.route("/calls", methods=["GET"])
@jwt_required()
def list_call_records():
    user_id = get_jwt_identity()
    result, error = capability_service.list_call_records(
        user_id=user_id,
        session_id=request.args.get("session_id"),
        agent_id=request.args.get("agent_id"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result)


@capability_bp.route("/<capability_id>", methods=["GET"])
@jwt_required()
def get_capability(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_service.get_capability(user_id, capability_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>/versions", methods=["GET"])
@jwt_required()
def get_capability_versions(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_service.get_versions(user_id, capability_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>/versions", methods=["POST"])
@jwt_required()
def create_capability_version(capability_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(CreateCapabilityVersionSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.create_user_version(
        user_id=user_id,
        capability_id=capability_id,
        content=data.get("content", ""),
        manifest=data.get("manifest"),
        permissions=data.get("permissions"),
        meta=data.get("meta"),
        version=data.get("version"),
        assets=data.get("assets"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capability version created", code=201)


@capability_bp.route("/<capability_id>/assets", methods=["GET"])
@jwt_required()
def list_capability_assets(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_import_confirm_service.list_assets(
        user_id=user_id,
        capability_id=capability_id,
        version_id=request.args.get("version_id"),
    )
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>/audits", methods=["GET"])
@jwt_required()
def list_capability_audits(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_import_confirm_service.list_audits(
        user_id=user_id,
        capability_id=capability_id,
    )
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>/provider-configs", methods=["GET"])
@jwt_required()
def list_tool_provider_configs(capability_id):
    user_id = get_jwt_identity()
    result, error = tool_provider_config_service.list_configs(user_id, capability_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>/provider-configs", methods=["POST"])
@jwt_required()
def create_tool_provider_config(capability_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(CreateToolProviderConfigSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = tool_provider_config_service.create_config(
        user_id=user_id,
        capability_id=capability_id,
        profile_name=data["profile_name"],
        provider_type=data["provider_type"],
        config=data.get("config"),
        secret_refs=data.get("secret_refs"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Provider config created", code=201)


@capability_bp.route("/<capability_id>/provider-configs/<config_id>", methods=["PUT"])
@jwt_required()
def update_tool_provider_config(capability_id, config_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(UpdateToolProviderConfigSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = tool_provider_config_service.update_config(
        user_id=user_id,
        capability_id=capability_id,
        config_id=config_id,
        **data,
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Provider config updated")


@capability_bp.route("/<capability_id>/provider-configs/<config_id>/test", methods=["POST"])
@jwt_required()
def test_tool_provider_config(capability_id, config_id):
    user_id = get_jwt_identity()
    result, error = tool_provider_config_service.test_config(
        user_id=user_id,
        capability_id=capability_id,
        config_id=config_id,
    )
    if error:
        return error_response(error, code=400, data=result)
    return success_response(result, message="Provider config tested")


@capability_bp.route("/<capability_id>/provider-configs/<config_id>/enable", methods=["POST"])
@jwt_required()
def enable_tool_provider_config(capability_id, config_id):
    user_id = get_jwt_identity()
    result, error = tool_provider_config_service.enable_config(
        user_id=user_id,
        capability_id=capability_id,
        config_id=config_id,
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Provider config enabled")


@capability_bp.route("/<capability_id>/provider-configs/<config_id>/disable", methods=["POST"])
@jwt_required()
def disable_tool_provider_config(capability_id, config_id):
    user_id = get_jwt_identity()
    result, error = tool_provider_config_service.disable_config(
        user_id=user_id,
        capability_id=capability_id,
        config_id=config_id,
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Provider config disabled")


@capability_bp.route("/<capability_id>/provider-configs/<config_id>", methods=["DELETE"])
@jwt_required()
def delete_tool_provider_config(capability_id, config_id):
    user_id = get_jwt_identity()
    result, error = tool_provider_config_service.delete_config(
        user_id=user_id,
        capability_id=capability_id,
        config_id=config_id,
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Provider config deleted")


@capability_bp.route("/<capability_id>/delete-impact", methods=["GET"])
@jwt_required()
def get_capability_delete_impact(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_service.get_delete_impact(user_id, capability_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@capability_bp.route("/<capability_id>", methods=["DELETE"])
@jwt_required()
def delete_capability(capability_id):
    user_id = get_jwt_identity()
    result, error = capability_service.archive_user_capability(user_id, capability_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capability archived")


@agent_capability_bp.route("/<agent_id>/capabilities", methods=["POST"])
@jwt_required()
def bind_agent_capability(agent_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(BindCapabilitySchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.bind_to_user_agent(
        user_id=user_id,
        agent_id=agent_id,
        capability_version_id=data["capability_version_id"],
        granted_permissions=data.get("granted_permissions", []),
        version_policy=data.get("version_policy", "pinned"),
        enabled=data.get("enabled", True),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Agent capability bound", code=201)


@agent_capability_bp.route("/<agent_id>/capabilities", methods=["GET"])
@jwt_required()
def list_agent_capabilities(agent_id):
    user_id = get_jwt_identity()
    result, error = capability_service.get_agent_bindings(agent_id, user_id=user_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@agent_capability_bp.route("/<agent_id>/capabilities/upgrades", methods=["GET"])
@jwt_required()
def list_agent_capability_upgrades(agent_id):
    user_id = get_jwt_identity()
    result, error = capability_service.get_user_agent_upgrade_status(user_id, agent_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@agent_capability_bp.route("/<agent_id>/capabilities/<binding_id>", methods=["PUT"])
@jwt_required()
def update_agent_capability(agent_id, binding_id):
    user_id = get_jwt_identity()
    data, validation_error = _load(UpdateCapabilityBindingSchema)
    if validation_error:
        return error_response(validation_error, code=400)
    result, error = capability_service.update_user_agent_binding(
        user_id=user_id,
        agent_id=agent_id,
        binding_id=binding_id,
        capability_version_id=data.get("capability_version_id"),
        granted_permissions=data.get("granted_permissions"),
        version_policy=data.get("version_policy", "pinned"),
        enabled=data.get("enabled"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Agent capability updated")


@agent_capability_bp.route("/<agent_id>/capabilities/<binding_id>", methods=["DELETE"])
@jwt_required()
def delete_agent_capability(agent_id, binding_id):
    user_id = get_jwt_identity()
    result, error = capability_service.delete_user_agent_binding(
        user_id=user_id,
        agent_id=agent_id,
        binding_id=binding_id,
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Agent capability unbound")
