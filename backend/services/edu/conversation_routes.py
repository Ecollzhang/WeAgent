"""Course-bound Education conversation bootstrap and context recovery."""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from .access import active_membership
from .agent_policy import (
    EducationAgentPolicyError,
    agents_for_role,
    resolve_agent_service_views,
    union_services,
)
from .content_models import Lesson
from .extensions import db
from .runtime_client import CoreRuntimeError
from .tool_gateway import (
    ToolGatewayError,
    catalog_for_role,
    issue_tool_grant,
)
from .workflow_models import EducationAgentRun, EducationConversationBinding
from .tool_models import EducationToolGrant


education_conversation_api = Blueprint("education_conversation_api", __name__)
MATERIAL_POLICIES = {"course_only", "authorized_knowledge"}


def _enabled(key, default=True):
    return bool(current_app.config.get(key, default))


def _binding_payload(binding, membership, lesson=None):
    return {
        "binding": binding.to_dict(),
        "course": {
            "id": membership.course.id,
            "title": membership.course.title,
            "subject_code": membership.course.subject_code,
            "grade_band": membership.course.grade_band,
            "membership_role": membership.role,
        },
        "lesson": (
            {
                "id": lesson.id,
                "title": lesson.title,
                "duration_minutes": lesson.duration_minutes,
                "status": lesson.status,
            }
            if lesson
            else None
        ),
        "agent_service_views": binding.agent_service_views or {},
    }


@education_conversation_api.get("/spec")
def education_service_spec():
    return jsonify(
        {
            "schema_version": "1.0",
            "domain": "edu",
            "service": current_app.config.get("SERVICE_NAME", "weagent-edu"),
            "capabilities": {
                "education": _enabled("EDUCATION_FEATURE_ENABLED"),
                "chat": _enabled("EDUCATION_CHAT_ENABLED"),
                "manual_create": _enabled("EDUCATION_CHAT_MANUAL_CREATE"),
                "tools": _enabled("EDUCATION_CHAT_TOOLS_ENABLED"),
                "rag": _enabled("EDUCATION_RAG_ENABLED"),
            },
            "endpoints": {
                "conversation_options": {
                    "method": "GET",
                    "path": "/api/edu/conversations/options",
                    "access": "course_member",
                },
                "conversation_bootstrap": {
                    "method": "POST",
                    "path": "/api/edu/conversations/bootstrap",
                    "access": "course_member",
                },
                "conversation_context": {
                    "method": "GET",
                    "path": "/api/edu/conversations/{conversation_id}/context",
                    "access": "bound_course_member",
                },
            },
        }
    )


@education_conversation_api.get("/conversations/options")
@jwt_required()
def conversation_options():
    if not _enabled("EDUCATION_CHAT_ENABLED"):
        return jsonify({"error": "Education chat is disabled"}), 404
    actor = get_jwt_identity()
    course_id = str(request.args.get("course_id") or "").strip()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    lessons = (
        Lesson.query.filter_by(course_id=course_id)
        .order_by(Lesson.position.asc(), Lesson.created_at.asc())
        .all()
    )
    return jsonify(
        {
            "course": membership.course.to_dict(membership.role),
            "membership_role": membership.role,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "duration_minutes": lesson.duration_minutes,
                    "status": lesson.status,
                }
                for lesson in lessons
                if membership.role == "teacher" or lesson.status == "published"
            ],
            "agents": agents_for_role(membership.role),
            "material_policies": [
                {
                    "value": "course_only",
                    "label": "仅当前课程资料",
                },
                {
                    "value": "authorized_knowledge",
                    "label": "允许检索已授权知识来源",
                },
            ],
        }
    )


@education_conversation_api.post("/conversations/bootstrap")
@jwt_required()
def bootstrap_conversation():
    if not _enabled("EDUCATION_CHAT_ENABLED") or not _enabled(
        "EDUCATION_CHAT_MANUAL_CREATE"
    ):
        return jsonify({"error": "Education chat is unavailable"}), 404
    actor = get_jwt_identity()
    payload = request.get_json(silent=True) or {}
    binding_mode = str(
        payload.get("binding_mode") or "manual"
    ).strip()
    if binding_mode not in {"manual", "course_bootstrap"}:
        return jsonify({"error": "invalid binding_mode"}), 400
    course_id = str(payload.get("course_id") or "").strip()
    if not course_id and binding_mode != "course_bootstrap":
        return jsonify({"error": "course_id is required"}), 400
    if course_id and binding_mode == "course_bootstrap":
        return jsonify(
            {"error": "course_bootstrap cannot target an existing course"}
        ), 400
    if binding_mode == "course_bootstrap" and not _enabled(
        "EDUCATION_COURSE_CREATION_ENABLED"
    ):
        return jsonify({"error": "course creation is disabled"}), 403
    membership = active_membership(course_id, actor) if course_id else None
    if course_id and not membership:
        return jsonify({"error": "course not found"}), 404
    membership_role = membership.role if membership else "course_creator"
    lesson_id = str(payload.get("lesson_id") or "").strip() or None
    lesson = None
    if lesson_id:
        if binding_mode == "course_bootstrap":
            return jsonify({"error": "lesson_id requires a course"}), 400
        lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first()
        if not lesson or (
            membership.role != "teacher" and lesson.status != "published"
        ):
            return jsonify({"error": "lesson not found"}), 404
    material_policy = str(
        payload.get("material_policy") or "course_only"
    ).strip()
    if material_policy not in MATERIAL_POLICIES:
        return jsonify({"error": "invalid material_policy"}), 400
    if binding_mode == "course_bootstrap":
        if payload.get("agent_ids") not in (None, [], ["_edu_1"]):
            return jsonify(
                {
                    "error": "course_bootstrap uses the course design Agent",
                    "error_code": "agent_role_mismatch",
                }
            ), 403
        agent_service_views = {"_edu_1": ["edu"]}
        material_policy = "course_only"
    else:
        try:
            agent_service_views = resolve_agent_service_views(
                payload.get("agent_ids"),
                role=membership.role,
                material_policy=material_policy,
                rag_enabled=_enabled("EDUCATION_RAG_ENABLED"),
            )
        except EducationAgentPolicyError as error:
            return jsonify(
                {"error": str(error), "error_code": error.error_code}
            ), 403 if error.error_code == "agent_role_mismatch" else 400
    services = union_services(agent_service_views)
    title = str(payload.get("title") or "").strip()[:200]
    if not title:
        target = (
            lesson.title
            if lesson
            else membership.course.title
            if membership
            else "创建新课程"
        )
        title = f"{target}｜Education 协作"
    visible_context = {
        "course": (
            {
                "id": membership.course.id,
                "title": membership.course.title,
            }
            if membership
            else None
        ),
        "lesson": (
            {"id": lesson.id, "title": lesson.title}
            if lesson
            else None
        ),
        "material_policy": material_policy,
    }
    runtime = current_app.extensions["education_runtime_client"]
    authorization = request.headers.get("Authorization", "")
    try:
        tool_grant, raw_tool_grant = issue_tool_grant(
            actor_user_id=actor,
            course_id=course_id or None,
            allowed_tools=(
                ["edu.course.list", "edu.course.create"]
                if binding_mode == "course_bootstrap"
                else [
                    item["name"]
                    for item in catalog_for_role(membership.role)
                ]
            ),
            capability_ids=["builtin:education_actions"],
            agent_ids=list(agent_service_views),
            lesson_id=lesson.id if lesson else None,
            grant_mode=(
                "course_bootstrap"
                if binding_mode == "course_bootstrap"
                else None
            ),
        )
    except ToolGatewayError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    # Core runs in a separate process and verifies this opaque grant before it
    # creates the sandbox. Persist it first so the verifier never observes an
    # uncommitted/non-existent authorization record.
    db.session.commit()
    try:
        conversation = runtime.create_conversation(
            authorization=authorization,
            title=title,
            agent_ids=list(agent_service_views),
            workspace_role=(
                membership.role
                if membership
                else "course_creator"
                if binding_mode == "course_bootstrap"
                else ""
            ),
            services=services,
            agent_service_views=agent_service_views,
            visible_context=visible_context,
            education_run_grant=raw_tool_grant,
        )
    except CoreRuntimeError as error:
        db.session.rollback()
        tool_grant.status = "revoked"
        tool_grant.revoked_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"error": str(error), "error_code": "core_unavailable"}), 503
    tool_grant.conversation_id = conversation["id"]
    binding = EducationConversationBinding(
        conversation_id=conversation["id"],
        actor_user_id=actor,
        course_id=course_id or None,
        lesson_id=lesson_id,
        membership_role_snapshot=membership_role,
        binding_mode=binding_mode,
        material_policy=material_policy,
        agent_service_views=agent_service_views,
        source_route=(
            payload.get("source_route")
            if isinstance(payload.get("source_route"), dict)
            else None
        ),
        status="active",
    )
    try:
        db.session.add(binding)
        db.session.commit()
    except Exception:
        db.session.rollback()
        persisted_grant = EducationToolGrant.query.get(tool_grant.id)
        if persisted_grant:
            persisted_grant.status = "revoked"
            persisted_grant.revoked_at = datetime.utcnow()
            db.session.commit()
        try:
            runtime.delete_conversation(
                authorization=authorization,
                conversation_id=conversation["id"],
            )
        except Exception:
            pass
        return jsonify(
            {
                "error": "Education conversation binding failed",
                "error_code": "binding_failed",
            }
        ), 500
    return jsonify(
        {
            "conversation": conversation,
            "binding": binding.to_dict(),
            "context": {
                **visible_context,
                "membership_role": membership_role,
            },
            "agent_service_views": agent_service_views,
        }
    ), 201


@education_conversation_api.get("/conversations/<conversation_id>/context")
@jwt_required()
def conversation_context(conversation_id):
    actor = get_jwt_identity()
    binding = EducationConversationBinding.query.filter_by(
        conversation_id=conversation_id,
        actor_user_id=actor,
        status="active",
    ).first()
    if not binding:
        return jsonify({"error": "Education conversation context not found"}), 404
    if binding.binding_mode == "course_bootstrap" and not binding.course_id:
        return jsonify(
            {
                "binding": binding.to_dict(),
                "course": None,
                "lesson": None,
                "agent_service_views": binding.agent_service_views or {},
                "run": None,
                "membership_role": "course_creator",
            }
        )
    if not binding.course_id:
        return jsonify({"error": "Education conversation context not found"}), 404
    membership = active_membership(binding.course_id, actor)
    if not membership:
        binding.status = "revoked"
        db.session.commit()
        return jsonify({"error": "Education conversation access was revoked"}), 403
    lesson = (
        Lesson.query.filter_by(
            id=binding.lesson_id,
            course_id=binding.course_id,
        ).first()
        if binding.lesson_id
        else None
    )
    payload = _binding_payload(binding, membership, lesson)
    run = (
        EducationAgentRun.query.filter_by(
            conversation_id=conversation_id,
            requested_by=actor,
        )
        .order_by(EducationAgentRun.created_at.desc())
        .first()
    )
    payload["run"] = run.to_dict() if run else None
    return jsonify(payload)


@education_conversation_api.post(
    "/conversations/<conversation_id>/access-check"
)
@jwt_required()
def conversation_access_check(conversation_id):
    """Fail-closed read check used before core exposes durable EDU cards."""
    claims = get_jwt()
    actor = str(claims.get("actor_user_id") or "").strip()
    if (
        get_jwt_identity() != "weagent-core-runtime"
        or claims.get("service") != "core"
        or not actor
    ):
        return jsonify(
            {
                "allowed": False,
                "error": "core service identity required",
                "error_code": "core_service_required",
            }
        ), 403
    binding = EducationConversationBinding.query.filter_by(
        conversation_id=conversation_id,
        actor_user_id=actor,
        status="active",
    ).first()
    if not binding:
        return jsonify({"allowed": False}), 404
    if binding.binding_mode == "course_bootstrap" and not binding.course_id:
        return jsonify({"allowed": True, "membership_role": "course_creator"})
    membership = (
        active_membership(binding.course_id, actor)
        if binding.course_id
        else None
    )
    if not membership:
        binding.status = "revoked"
        db.session.commit()
        return jsonify({"allowed": False}), 403
    return jsonify(
        {
            "allowed": True,
            "course_id": binding.course_id,
            "membership_role": membership.role,
        }
    )


@education_conversation_api.post(
    "/conversations/<conversation_id>/runtime-grant"
)
@jwt_required()
def rotate_conversation_runtime_grant(conversation_id):
    """Issue a fresh short-lived grant only to the authenticated core service.

    The raw grant is never stored in either database and is intentionally not
    available through a normal end-user JWT.  This is the durable-runtime
    recovery boundary used after a sandbox/container restart.
    """
    claims = get_jwt()
    actor = str(claims.get("actor_user_id") or "").strip()
    if (
        get_jwt_identity() != "weagent-core-runtime"
        or claims.get("service") != "core"
        or not actor
    ):
        return jsonify(
            {
                "error": "core service identity required",
                "error_code": "core_service_required",
            }
        ), 403
    if not _enabled("EDUCATION_CHAT_ENABLED") or not _enabled(
        "EDUCATION_CHAT_TOOLS_ENABLED"
    ):
        return jsonify({"error": "Education chat tools are disabled"}), 404
    binding = EducationConversationBinding.query.filter_by(
        conversation_id=conversation_id,
        actor_user_id=actor,
        status="active",
    ).first()
    if not binding:
        return jsonify(
            {
                "error": "Education conversation context not found",
                "error_code": "binding_not_found",
            }
        ), 404
    course_bootstrap = (
        binding.binding_mode == "course_bootstrap"
        and not binding.course_id
    )
    membership = (
        active_membership(binding.course_id, actor)
        if binding.course_id
        else None
    )
    if not membership and not course_bootstrap:
        binding.status = "revoked"
        db.session.commit()
        return jsonify(
            {
                "error": "Education conversation access was revoked",
                "error_code": "membership_revoked",
            }
        ), 403
    if course_bootstrap:
        views = {"_edu_1": ["edu"]}
        membership_role = "course_creator"
    else:
        try:
            views = resolve_agent_service_views(
                list((binding.agent_service_views or {}).keys()),
                role=membership.role,
                material_policy=binding.material_policy,
                rag_enabled=_enabled("EDUCATION_RAG_ENABLED"),
            )
        except EducationAgentPolicyError as error:
            binding.status = "revoked"
            db.session.commit()
            return jsonify(
                {"error": str(error), "error_code": error.error_code}
            ), 409
        membership_role = membership.role
    now = datetime.utcnow()
    old_grants = EducationToolGrant.query.filter_by(
        conversation_id=conversation_id,
        actor_user_id=actor,
        status="active",
    ).all()
    for old_grant in old_grants:
        old_grant.status = "revoked"
        old_grant.revoked_at = now
    try:
        linked_run = (
            EducationAgentRun.query.filter_by(
                conversation_id=conversation_id,
                requested_by=actor,
            )
            .order_by(EducationAgentRun.created_at.desc())
            .first()
        )
        confirmed_actions = (
            (linked_run.input_payload or {}).get("confirmed_actions") or []
            if linked_run
            else []
        )
        grant, raw_grant = issue_tool_grant(
            actor_user_id=actor,
            course_id=binding.course_id,
            allowed_tools=(
                ["edu.course.list", "edu.course.create"]
                if course_bootstrap
                else [
                    item["name"]
                    for item in catalog_for_role(membership.role)
                ]
            ),
            capability_ids=["builtin:education_actions"],
            agent_ids=list(views),
            lesson_id=binding.lesson_id,
            conversation_id=conversation_id,
            grant_mode="course_bootstrap" if course_bootstrap else None,
            confirmed_actions=confirmed_actions,
        )
        binding.membership_role_snapshot = membership_role
        binding.agent_service_views = views
        db.session.commit()
    except ToolGatewayError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    return jsonify(
        {
            "run_grant": raw_grant,
            "grant_id": grant.id,
            "membership_role": membership_role,
            "course_id": binding.course_id,
            "lesson_id": binding.lesson_id,
            "agent_service_views": views,
            "services": union_services(views),
        }
    ), 201
