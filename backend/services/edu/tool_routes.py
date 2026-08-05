"""HTTP boundary for JWT grant issuance and opaque Agent tool invocation."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .access import active_membership
from .extensions import db
from .tool_gateway import (
    ToolGatewayError,
    catalog_for_role,
    invoke_tool,
    issue_tool_grant,
    resolve_grant,
)
from .tool_models import EducationToolCall, EducationToolGrant


education_tool_api = Blueprint("education_tool_api", __name__)


def _error(error):
    return jsonify(
        {"error": error.message, "error_code": error.error_code}
    ), error.status_code


@education_tool_api.post("/tool-grants/verify-runtime")
def verify_runtime_grant():
    """Verify one opaque grant for the core runtime without exposing its scope."""
    token = str(
        request.headers.get("X-Education-Run-Grant") or ""
    ).strip()
    actor_user_id = str(
        (request.get_json(silent=True) or {}).get("actor_user_id") or ""
    ).strip()
    try:
        grant = resolve_grant(token)
    except ToolGatewayError:
        db.session.rollback()
        return jsonify({"valid": False}), 403
    if (
        not actor_user_id
        or grant.actor_user_id != actor_user_id
        or "builtin:education_actions" not in (grant.capability_ids or [])
    ):
        return jsonify({"valid": False}), 403
    return jsonify({"valid": True})


@education_tool_api.get("/tools/catalog")
@jwt_required()
def get_tool_catalog():
    actor = get_jwt_identity()
    course_id = str(request.args.get("course_id") or "").strip()
    if course_id:
        membership = active_membership(course_id, actor)
        if not membership:
            return jsonify({"error": "course not found"}), 404
        role = membership.role
    else:
        role = "teacher"
    return jsonify(
        {
            "course_id": course_id or None,
            "actor_role": role,
            "items": catalog_for_role(role),
        }
    )


@education_tool_api.post("/tool-grants")
@jwt_required()
def create_tool_grant():
    data = request.get_json(silent=True) or {}
    try:
        grant, raw_token = issue_tool_grant(
            actor_user_id=get_jwt_identity(),
            course_id=str(data.get("course_id") or "").strip() or None,
            allowed_tools=data.get("allowed_tools") or [],
            capability_ids=data.get("capability_ids") or [],
            agent_ids=data.get("agent_ids") or [],
            lesson_id=data.get("lesson_id"),
            agent_run_id=data.get("agent_run_id"),
            conversation_id=data.get("conversation_id"),
            ttl_seconds=data.get("ttl_seconds"),
            confirmed_actions=data.get("confirmed_actions") or [],
        )
        db.session.commit()
    except (ToolGatewayError, TypeError, ValueError) as error:
        db.session.rollback()
        if not isinstance(error, ToolGatewayError):
            error = ToolGatewayError(
                "ttl_seconds must be an integer",
                400,
                "invalid_grant_ttl",
            )
        return _error(error)
    payload = grant.to_dict()
    payload["token"] = raw_token
    return jsonify(payload), 201


@education_tool_api.post("/tools/<path:tool_name>/invoke")
def invoke_agent_tool(tool_name):
    data = request.get_json(silent=True) or {}
    raw_token = (
        request.headers.get("X-Education-Run-Grant")
        or str(data.get("run_grant") or "")
    ).strip()
    try:
        call, result, replayed = invoke_tool(
            raw_token=raw_token,
            tool_name=tool_name,
            arguments=data.get("arguments") or {},
            idempotency_key=data.get("idempotency_key"),
            agent_id=data.get("agent_id"),
        )
    except ToolGatewayError as error:
        db.session.rollback()
        return _error(error)
    return jsonify(
        {
            "call_id": call.id,
            "tool_name": tool_name,
            "replayed": replayed,
            "result": result,
        }
    )


@education_tool_api.get("/courses/<course_id>/tool-calls")
@jwt_required()
def list_tool_calls(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = EducationToolCall.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(actor_user_id=actor)
    run_id = str(request.args.get("agent_run_id") or "").strip()
    if run_id:
        query = query.join(
            EducationToolGrant,
            EducationToolCall.grant_id == EducationToolGrant.id,
        ).filter(EducationToolGrant.agent_run_id == run_id)
    rows = query.order_by(EducationToolCall.created_at.desc()).limit(200).all()
    return jsonify({"items": [row.to_dict() for row in rows]})
