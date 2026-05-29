from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.schemas.capability_schema import (
    BindCapabilitySchema,
    CallSyncSchema,
    CreateCapabilityVersionSchema,
    CreateSkillSchema,
    DraftForkSchema,
    DraftPublishSchema,
    ImportMarkdownSchema,
    ImportNpxManifestSchema,
    UpdateCapabilityBindingSchema,
)
from app.services.capability_call_sync_service import capability_call_sync_service
from app.services.capability_service import capability_service
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
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capabilities imported", code=201)


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
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Capability version created", code=201)


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
