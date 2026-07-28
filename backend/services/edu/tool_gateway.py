"""Controlled Agent-to-Education application service gateway.

The model never supplies an actor or a course scope. Those values are projected
from a short-lived server-issued grant and revalidated before every call.
"""

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import or_

from .access import active_membership
from .asset_service import AssetServiceError, asset_to_dict, create_database_asset
from .content_models import (
    CourseUnit,
    EducationContent,
    EducationContentVersion,
    Lesson,
)
from .extensions import db
from .knowledge_models import AssessmentItem, AssessmentPaper, KnowledgeResource
from .knowledge_service import (
    KnowledgeServiceError,
    compose_paper,
    create_question,
    knowledge_resource_to_dict,
    paper_to_dict,
    publish_question,
    question_to_dict,
)
from .learning_service import (
    LearningServiceError,
    attempt_to_dict,
    create_mind_map,
    create_mock_exam,
    create_weakness_snapshot,
    insight_to_dict,
    mind_map_to_dict,
    refresh_student_insights,
    weakness_to_dict,
)
from .models import Course, CourseMemberProfile, CourseMembership
from .tool_models import EducationToolCall, EducationToolGrant


TEACHER = "teacher"
STUDENT = "student"
RESERVED_SCOPE_ARGUMENTS = {
    "actor",
    "actor_id",
    "actor_user_id",
    "course",
    "course_id",
    "membership_role",
    "role",
    "user_id",
}
SENSITIVE_PARTS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
}


def _object_schema(properties=None, required=None):
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


QUESTION_SCHEMA = _object_schema(
    {
        "title": {"type": "string"},
        "question_type": {
            "type": "string",
            "enum": [
                "single_choice",
                "multiple_choice",
                "fill_blank",
                "short_answer",
                "writing",
            ],
        },
        "prompt": {"type": "string"},
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Plain option text without A/B or numeric labels.",
        },
        "difficulty": {
            "type": "string",
            "enum": ["easy", "medium", "hard"],
        },
        "score": {"type": "number"},
        "knowledge_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "correct_answer": {},
        "explanation": {"type": "string"},
        "rubric": {"type": "object"},
        "grade_band": {"type": "string"},
        "source_context": {"type": "object"},
    },
    [
        "title",
        "question_type",
        "prompt",
        "difficulty",
        "score",
        "knowledge_points",
        "correct_answer",
    ],
)


TOOL_CATALOG = {
    "edu.course.list": {
        "description": "List courses visible to the granted actor.",
        "roles": [TEACHER, STUDENT],
        "mode": "read",
        "input_schema": _object_schema(),
    },
    "edu.course.members.list": {
        "description": "List the active roster for the granted course.",
        "roles": [TEACHER],
        "mode": "read",
        "input_schema": _object_schema(),
    },
    "edu.course.context.get": {
        "description": "Read the granted course structure and asset counts.",
        "roles": [TEACHER, STUDENT],
        "mode": "read",
        "input_schema": _object_schema(),
    },
    "edu.question_bank.search": {
        "description": "Search the granted course question bank.",
        "roles": [TEACHER, STUDENT],
        "mode": "read",
        "input_schema": _object_schema(
            {
                "query": {"type": "string"},
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                },
                "limit": {"type": "integer"},
            }
        ),
    },
    "edu.knowledge.search": {
        "description": "Search course knowledge-resource metadata and source links.",
        "roles": [TEACHER, STUDENT],
        "mode": "read",
        "input_schema": _object_schema(
            {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            }
        ),
    },
    "edu.course.create": {
        "description": "Create a supported Education course for the actor.",
        "roles": [TEACHER],
        "mode": "write",
        "course_optional": True,
        "input_schema": _object_schema(
            {
                "title": {"type": "string"},
                "subject_code": {
                    "type": "string",
                    "enum": ["high_school_english", "primary_chinese"],
                },
                "grade_band": {
                    "type": "string",
                    "enum": ["senior_high", "primary"],
                },
                "description": {"type": "string"},
            },
            ["title", "subject_code", "grade_band"],
        ),
    },
    "edu.course.members.import": {
        "description": "Import or reactivate a bounded list of student account IDs.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "members": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "display_name": {"type": "string"},
                        },
                        "required": ["user_id"],
                        "additionalProperties": False,
                    },
                },
                "atomic": {"type": "boolean"},
            },
            ["members"],
        ),
    },
    "edu.lesson.create": {
        "description": "Create a classified lesson draft in the granted course.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "title": {"type": "string"},
                "unit_id": {"type": "string"},
                "learning_domain": {
                    "type": "string",
                    "enum": ["reading", "writing", "integrated"],
                },
                "theme_code": {"type": "string"},
                "text_genre_code": {"type": "string"},
                "lesson_type_code": {
                    "type": "string",
                    "enum": [
                        "reading",
                        "writing",
                        "reading_writing",
                        "integrated",
                    ],
                },
                "duration_minutes": {"type": "integer"},
                "position": {"type": "integer"},
            },
            [
                "title",
                "learning_domain",
                "text_genre_code",
                "lesson_type_code",
                "duration_minutes",
            ],
        ),
    },
    "edu.courseware.create": {
        "description": "Adopt structured slide or rich-document output as a versioned draft.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "lesson_id": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["slide_document", "rich_document", "lesson_plan"],
                },
                "schema_name": {"type": "string"},
                "schema_version": {"type": "string"},
                "source_json": {"type": "object"},
                "rendered_html": {"type": "string"},
                "change_summary": {"type": "string"},
                "source_agent_run_id": {"type": "string"},
            },
            ["lesson_id", "kind", "schema_name", "source_json"],
        ),
    },
    "edu.asset.attach": {
        "description": "Adopt generated bytes or text into durable course-owned storage.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "lesson_id": {"type": "string"},
                "title": {"type": "string"},
                "original_filename": {"type": "string"},
                "media_type": {"type": "string"},
                "purpose": {"type": "string"},
                "visibility_scope": {
                    "type": "string",
                    "enum": ["owner_private", "course_teacher", "course_published"],
                },
                "content_base64": {"type": "string"},
                "text_content": {"type": "string"},
                "source_agent_run_id": {"type": "string"},
            },
            ["title", "original_filename", "media_type"],
        ),
    },
    "edu.question_bank.upsert": {
        "description": "Validate and adopt canonical questions into the course bank.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "questions": {
                    "type": "array",
                    "items": QUESTION_SCHEMA,
                },
                "publish": {"type": "boolean"},
                "source_agent_run_id": {"type": "string"},
            },
            ["questions"],
        ),
    },
    "edu.paper.compose": {
        "description": "Compose a version-frozen paper from published question IDs.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "title": {"type": "string"},
                "purpose": {
                    "type": "string",
                    "enum": ["practice", "assignment", "mock_exam", "diagnostic"],
                },
                "duration_minutes": {"type": "integer"},
                "item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "sections": {"type": "array"},
            },
            ["title", "duration_minutes", "item_ids"],
        ),
    },
    "edu.student_insight.refresh": {
        "description": "Refresh evidence-backed student insight snapshots.",
        "roles": [TEACHER],
        "mode": "write",
        "input_schema": _object_schema(),
    },
    "edu.mock_exam.create": {
        "description": "Create a private mock-exam attempt for the granted student.",
        "roles": [STUDENT],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "title": {"type": "string"},
                "paper_id": {"type": "string"},
                "question_count": {"type": "integer"},
                "duration_minutes": {"type": "integer"},
                "difficulty_mix": {"type": "object"},
                "knowledge_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            }
        ),
    },
    "edu.weakness.analyze": {
        "description": "Create an evidence-linked weakness snapshot for the student.",
        "roles": [STUDENT],
        "mode": "write",
        "input_schema": _object_schema(),
    },
    "edu.mind_map.create": {
        "description": "Create a versioned course mind map owned by the student.",
        "roles": [STUDENT],
        "mode": "write",
        "input_schema": _object_schema(
            {
                "title": {"type": "string"},
                "tree": {"type": "object"},
                "source_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            }
        ),
    },
}


@dataclass
class ToolGatewayError(Exception):
    message: str
    status_code: int = 400
    error_code: str = "invalid_tool_request"


def token_hash(raw_token):
    return hashlib.sha256(str(raw_token).encode("utf-8")).hexdigest()


def _payload_hash(value):
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sanitize(value, key=""):
    lowered = str(key or "").lower()
    if any(part in lowered for part in SENSITIVE_PARTS):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: _sanitize(item, str(item_key))
            for item_key, item in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:500]


def _summary(value):
    if isinstance(value, dict):
        result = {"keys": sorted(value.keys())[:20]}
        items = value.get("items")
        if isinstance(items, list):
            result["item_count"] = len(items)
        for key in (
            "id",
            "course_id",
            "status",
            "data_state",
            "student_user_id",
        ):
            if key in value:
                result[key] = value[key]
        return result
    if isinstance(value, list):
        return {"item_count": len(value)}
    return {"type": type(value).__name__}


def _tool_record(name):
    definition = TOOL_CATALOG.get(name)
    if not definition:
        raise ToolGatewayError("tool not found", 404, "tool_not_found")
    return definition


def catalog_for_role(role):
    return [
        {
            "name": name,
            "description": definition["description"],
            "mode": definition["mode"],
            "input_schema": definition["input_schema"],
        }
        for name, definition in TOOL_CATALOG.items()
        if role in definition["roles"]
    ]


def _resolve_role(course_id, actor_user_id):
    if not course_id:
        return TEACHER
    membership = active_membership(course_id, actor_user_id)
    if not membership:
        raise ToolGatewayError("course not found", 404, "course_not_found")
    return membership.role


def issue_tool_grant(
    *,
    actor_user_id,
    course_id,
    allowed_tools,
    capability_ids=None,
    agent_run_id=None,
    conversation_id=None,
    ttl_seconds=None,
):
    role = _resolve_role(course_id, actor_user_id)
    requested = list(dict.fromkeys(str(item) for item in (allowed_tools or [])))
    if not requested:
        raise ToolGatewayError(
            "allowed_tools must contain at least one tool",
            400,
            "allowed_tools_required",
        )
    if len(requested) > 30:
        raise ToolGatewayError(
            "too many tools requested",
            400,
            "too_many_tools",
        )
    for name in requested:
        definition = _tool_record(name)
        if role not in definition["roles"]:
            raise ToolGatewayError(
                f"{name} is not available to {role}",
                403,
                "tool_role_forbidden",
            )
        if not course_id and not definition.get("course_optional"):
            raise ToolGatewayError(
                f"{name} requires a course scope",
                400,
                "course_scope_required",
            )
    configured_ttl = int(
        current_app.config.get("EDUCATION_TOOL_GRANT_TTL_SECONDS", 900)
    )
    ttl = int(ttl_seconds or configured_ttl)
    ttl = max(30, min(ttl, 3600))
    raw_token = secrets.token_urlsafe(36)
    grant = EducationToolGrant(
        token_hash=token_hash(raw_token),
        course_id=course_id or None,
        actor_user_id=actor_user_id,
        actor_role=role,
        allowed_tools=requested,
        capability_ids=[
            str(value)[:100] for value in (capability_ids or [])[:30]
        ],
        agent_run_id=str(agent_run_id or "")[:100] or None,
        conversation_id=str(conversation_id or "")[:100] or None,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl),
    )
    db.session.add(grant)
    db.session.flush()
    return grant, raw_token


def resolve_grant(raw_token):
    if not raw_token:
        raise ToolGatewayError(
            "Education run grant is required",
            401,
            "tool_grant_required",
        )
    grant = EducationToolGrant.query.filter_by(
        token_hash=token_hash(raw_token)
    ).first()
    if not grant:
        raise ToolGatewayError(
            "Education run grant is invalid",
            401,
            "tool_grant_invalid",
        )
    if grant.status != "active":
        raise ToolGatewayError(
            "Education run grant is inactive",
            401,
            "tool_grant_inactive",
        )
    if grant.expires_at <= datetime.utcnow():
        grant.status = "expired"
        db.session.commit()
        raise ToolGatewayError(
            "Education run grant has expired",
            401,
            "tool_grant_expired",
        )
    if grant.course_id:
        membership = active_membership(grant.course_id, grant.actor_user_id)
        if not membership or membership.role != grant.actor_role:
            raise ToolGatewayError(
                "Education run grant scope is no longer valid",
                401,
                "tool_grant_scope_invalid",
            )
    return grant


def _course_dict(course, role=None):
    return course.to_dict(membership_role=role)


def _list_courses(grant, _arguments):
    rows = (
        db.session.query(Course, CourseMembership)
        .join(CourseMembership, CourseMembership.course_id == Course.id)
        .filter(
            CourseMembership.user_id == grant.actor_user_id,
            CourseMembership.status == "active",
            Course.status != "archived",
        )
        .order_by(Course.created_at.asc())
        .all()
    )
    return {
        "items": [_course_dict(course, membership.role) for course, membership in rows]
    }


def _list_members(grant, _arguments):
    members = (
        CourseMembership.query.filter_by(
            course_id=grant.course_id,
            status="active",
        )
        .order_by(CourseMembership.created_at.asc())
        .all()
    )
    profiles = {
        profile.user_id: profile.display_name
        for profile in CourseMemberProfile.query.filter_by(
            course_id=grant.course_id
        ).all()
    }
    return {
        "items": [
            {
                **member.to_dict(),
                "display_name": profiles.get(member.user_id) or member.user_id,
            }
            for member in members
        ]
    }


def _course_context(grant, _arguments):
    course = Course.query.filter_by(id=grant.course_id, status="active").first()
    if not course:
        raise ToolGatewayError("course not found", 404, "course_not_found")
    units = CourseUnit.query.filter_by(
        course_id=course.id,
        status="active",
    ).count()
    lessons = Lesson.query.filter_by(course_id=course.id).count()
    questions = AssessmentItem.query.filter_by(course_id=course.id).count()
    papers = AssessmentPaper.query.filter_by(course_id=course.id).count()
    resources = KnowledgeResource.query.filter_by(
        course_id=course.id,
        status="active",
    ).count()
    return {
        "course": _course_dict(course, grant.actor_role),
        "counts": {
            "units": units,
            "lessons": lessons,
            "questions": questions,
            "papers": papers,
            "knowledge_resources": resources,
        },
    }


def _question_search(grant, arguments):
    query = AssessmentItem.query.filter_by(course_id=grant.course_id)
    if grant.actor_role != TEACHER:
        query = query.filter_by(status="published")
    else:
        query = query.filter(AssessmentItem.status != "archived")
    text = str(arguments.get("query") or "").strip()
    if text:
        query = query.filter(AssessmentItem.title.ilike(f"%{text}%"))
    rows = query.order_by(AssessmentItem.updated_at.desc()).all()
    difficulty = str(arguments.get("difficulty") or "").strip()
    limit = max(1, min(int(arguments.get("limit") or 20), 100))
    items = []
    for row in rows:
        item = question_to_dict(
            row,
            include_answer=grant.actor_role == TEACHER,
        )
        version = item.get("current_version") or {}
        if difficulty and version.get("difficulty") != difficulty:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return {"items": items, "query": text}


def _knowledge_search(grant, arguments):
    query = KnowledgeResource.query.filter_by(
        course_id=grant.course_id,
        status="active",
    )
    if grant.actor_role != TEACHER:
        query = query.filter_by(visibility_scope="course_published")
    text = str(arguments.get("query") or "").strip()
    if text:
        query = query.filter(
            or_(
                KnowledgeResource.title.ilike(f"%{text}%"),
                KnowledgeResource.resource_type.ilike(f"%{text}%"),
            )
        )
    limit = max(1, min(int(arguments.get("limit") or 10), 50))
    rows = query.order_by(KnowledgeResource.updated_at.desc()).limit(limit).all()
    return {
        "items": [knowledge_resource_to_dict(row) for row in rows],
        "query": text,
        "retrieval_mode": "metadata",
    }


def _create_course(grant, arguments):
    title = str(arguments.get("title") or "").strip()
    subject_code = str(arguments.get("subject_code") or "").strip()
    grade_band = str(arguments.get("grade_band") or "").strip()
    supported = {
        ("high_school_english", "senior_high"),
        ("primary_chinese", "primary"),
    }
    if not title:
        raise ToolGatewayError("title is required", 400, "course_title_required")
    if (subject_code, grade_band) not in supported:
        raise ToolGatewayError(
            "unsupported subject_code and grade_band",
            400,
            "unsupported_course",
        )
    course = Course(
        title=title,
        subject_code=subject_code,
        grade_band=grade_band,
        description=str(arguments.get("description") or "").strip(),
        owner_user_id=grant.actor_user_id,
        status="active",
    )
    membership = CourseMembership(
        course=course,
        user_id=grant.actor_user_id,
        role=TEACHER,
        status="active",
        joined_at=datetime.utcnow(),
    )
    db.session.add_all([course, membership])
    db.session.flush()
    return _course_dict(course, TEACHER)


def _import_members(grant, arguments):
    members = arguments.get("members")
    if not isinstance(members, list) or not members or len(members) > 200:
        raise ToolGatewayError(
            "members must contain 1 to 200 rows",
            400,
            "invalid_member_list",
        )
    atomic = arguments.get("atomic") is True
    seen = set()
    prepared = []
    failures = []

    def reject(index, user_id, message, error_code, status_code=400):
        failure = {
            "row_index": index,
            "user_id": user_id or None,
            "error": message,
            "error_code": error_code,
            "status_code": status_code,
        }
        failures.append(failure)
        return failure

    for index, item in enumerate(members):
        if not isinstance(item, dict):
            reject(
                index,
                None,
                f"members[{index}] must be an object",
                "invalid_member_row",
            )
            continue
        user_id = str(item.get("user_id") or "").strip()
        display_name = str(item.get("display_name") or "").strip()
        if not user_id or len(user_id) > 100 or user_id in seen:
            reject(
                index,
                user_id,
                f"members[{index}].user_id is invalid or duplicated",
                "invalid_member_row",
            )
            continue
        if display_name and len(display_name) > 80:
            reject(
                index,
                user_id,
                f"members[{index}].display_name is too long",
                "invalid_member_row",
            )
            continue
        seen.add(user_id)
        membership = CourseMembership.query.filter_by(
            course_id=grant.course_id,
            user_id=user_id,
        ).first()
        if membership and membership.role == TEACHER:
            reject(
                index,
                user_id,
                f"members[{index}] is already a teacher",
                "member_role_conflict",
                409,
            )
            continue
        prepared.append((index, user_id, display_name, membership))

    if atomic and failures:
        first = failures[0]
        raise ToolGatewayError(
            first["error"],
            first["status_code"],
            first["error_code"],
        )

    rows = []
    for _index, user_id, display_name, membership in prepared:
        if membership:
            membership.role = STUDENT
            membership.status = "active"
            membership.invited_by = grant.actor_user_id
            membership.joined_at = membership.joined_at or datetime.utcnow()
            membership.removed_at = None
        else:
            membership = CourseMembership(
                course_id=grant.course_id,
                user_id=user_id,
                role=STUDENT,
                status="active",
                invited_by=grant.actor_user_id,
                joined_at=datetime.utcnow(),
            )
            db.session.add(membership)
        if display_name:
            profile = CourseMemberProfile.query.filter_by(
                course_id=grant.course_id,
                user_id=user_id,
            ).first()
            if profile:
                profile.display_name = display_name
            else:
                db.session.add(
                    CourseMemberProfile(
                        course_id=grant.course_id,
                        user_id=user_id,
                        display_name=display_name,
                    )
                )
        rows.append(
            {
                "user_id": user_id,
                "display_name": display_name or user_id,
                "role": STUDENT,
                "status": "active",
            }
        )
    db.session.flush()
    return {
        "items": rows,
        "failures": failures,
        "imported_count": len(rows),
        "failed_count": len(failures),
        "atomic": atomic,
    }


def _lesson_dict(lesson):
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "learning_domain": lesson.learning_domain,
        "theme_code": lesson.theme_code,
        "text_genre_code": lesson.text_genre_code,
        "lesson_type_code": lesson.lesson_type_code,
        "duration_minutes": lesson.duration_minutes,
        "position": lesson.position,
        "status": lesson.status,
    }


def _create_lesson(grant, arguments):
    course = Course.query.filter_by(id=grant.course_id, status="active").first()
    if not course:
        raise ToolGatewayError("course not found", 404, "course_not_found")
    supported_genres = {
        "high_school_english": {
            "narrative",
            "expository",
            "argumentative",
            "practical",
            "news",
            "biography",
            "literary",
        },
        "primary_chinese": {
            "narrative",
            "scenery",
            "expository",
            "fairy_tale",
            "fable",
            "poetry",
            "ancient_poetry",
            "practical",
            "composition",
        },
    }
    title = str(arguments.get("title") or "").strip()
    domain = str(arguments.get("learning_domain") or "")
    genre = str(arguments.get("text_genre_code") or "")
    lesson_type = str(arguments.get("lesson_type_code") or "")
    if (
        not title
        or domain not in {"reading", "writing", "integrated"}
        or genre not in supported_genres.get(course.subject_code, set())
        or lesson_type
        not in {"reading", "writing", "reading_writing", "integrated"}
    ):
        raise ToolGatewayError(
            "lesson classification is not supported by subject template",
            400,
            "invalid_lesson_classification",
        )
    unit_id = str(arguments.get("unit_id") or "").strip() or None
    if unit_id and not CourseUnit.query.filter_by(
        id=unit_id,
        course_id=course.id,
        status="active",
    ).first():
        raise ToolGatewayError("unit not found", 404, "unit_not_found")
    try:
        duration = int(arguments.get("duration_minutes") or 0)
        position = int(arguments.get("position") or 0)
    except (TypeError, ValueError) as exc:
        raise ToolGatewayError(
            "duration and position must be integers",
            400,
            "invalid_lesson_numbers",
        ) from exc
    if not 1 <= duration <= 600:
        raise ToolGatewayError(
            "duration_minutes must be between 1 and 600",
            400,
            "invalid_lesson_duration",
        )
    lesson = Lesson(
        course_id=course.id,
        unit_id=unit_id,
        title=title,
        learning_domain=domain,
        theme_code=str(arguments.get("theme_code") or "").strip(),
        text_genre_code=genre,
        lesson_type_code=lesson_type,
        duration_minutes=duration,
        position=position,
    )
    db.session.add(lesson)
    db.session.flush()
    return _lesson_dict(lesson)


def _checksum(value):
    return _payload_hash(value)


def _courseware_create(grant, arguments):
    lesson_id = str(arguments.get("lesson_id") or "").strip()
    lesson = Lesson.query.filter_by(
        id=lesson_id,
        course_id=grant.course_id,
    ).first()
    if not lesson:
        raise ToolGatewayError("lesson not found", 404, "lesson_not_found")
    kind = str(arguments.get("kind") or "")
    if kind not in {"slide_document", "rich_document", "lesson_plan"}:
        raise ToolGatewayError(
            "unsupported courseware kind",
            400,
            "invalid_courseware_kind",
        )
    source = arguments.get("source_json")
    schema_name = str(arguments.get("schema_name") or "").strip()
    if not isinstance(source, dict) or not schema_name:
        raise ToolGatewayError(
            "schema_name and object source_json are required",
            400,
            "invalid_courseware_payload",
        )
    if kind == "lesson_plan":
        required = {
            "subject_code",
            "learning_domain",
            "text_genre_code",
            "objectives",
            "stages",
        }
        if (
            not required.issubset(source)
            or not isinstance(source.get("objectives"), list)
            or not source["objectives"]
            or not isinstance(source.get("stages"), list)
            or not source["stages"]
        ):
            raise ToolGatewayError(
                "lesson plan is missing required structured fields",
                400,
                "invalid_lesson_plan",
            )
        course = Course.query.get(grant.course_id)
        if (
            source["subject_code"] != course.subject_code
            or source["learning_domain"] != lesson.learning_domain
            or source["text_genre_code"] != lesson.text_genre_code
        ):
            raise ToolGatewayError(
                "lesson plan does not match lesson classification",
                400,
                "lesson_plan_scope_mismatch",
            )
    content = EducationContent(
        course_id=grant.course_id,
        lesson_id=lesson.id,
        kind=kind,
        owner_user_id=grant.actor_user_id,
        visibility_scope="course_teacher",
        status="draft",
    )
    db.session.add(content)
    db.session.flush()
    version = EducationContentVersion(
        content_id=content.id,
        version_number=1,
        schema_name=schema_name,
        schema_version=str(arguments.get("schema_version") or "1.0"),
        source_json=source,
        rendered_html=arguments.get("rendered_html"),
        change_summary=str(arguments.get("change_summary") or "Agent draft")[:500],
        created_by_user_id=grant.actor_user_id,
        source_agent_run_id=str(arguments.get("source_agent_run_id") or "")[:100]
        or grant.agent_run_id,
        checksum=_checksum(source),
    )
    db.session.add(version)
    db.session.flush()
    content.current_version_id = version.id
    return {
        "content": {
            "id": content.id,
            "course_id": content.course_id,
            "lesson_id": content.lesson_id,
            "kind": content.kind,
            "status": content.status,
            "current_version_id": content.current_version_id,
        },
        "version": {
            "id": version.id,
            "version_number": version.version_number,
            "schema_name": version.schema_name,
            "schema_version": version.schema_version,
            "checksum": version.checksum,
        },
    }


def _attach_asset(grant, arguments):
    lesson_id = str(arguments.get("lesson_id") or "").strip() or None
    if lesson_id and not Lesson.query.filter_by(
        id=lesson_id,
        course_id=grant.course_id,
    ).first():
        raise ToolGatewayError("lesson not found", 404, "lesson_not_found")
    encoded = arguments.get("content_base64")
    text_content = arguments.get("text_content")
    if encoded and text_content is not None:
        raise ToolGatewayError(
            "provide content_base64 or text_content, not both",
            400,
            "ambiguous_asset_content",
        )
    try:
        content = (
            base64.b64decode(str(encoded), validate=True)
            if encoded
            else str(text_content or "").encode("utf-8")
        )
    except (ValueError, TypeError) as exc:
        raise ToolGatewayError(
            "content_base64 is invalid",
            400,
            "invalid_asset_content",
        ) from exc
    max_bytes = int(
        current_app.config.get("EDUCATION_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
    )
    if not content or len(content) > max_bytes:
        raise ToolGatewayError(
            "asset is empty or exceeds the upload limit",
            400,
            "invalid_asset_size",
        )
    asset = create_database_asset(
        course_id=grant.course_id,
        lesson_id=lesson_id,
        actor_user_id=grant.actor_user_id,
        content=content,
        original_filename=str(arguments.get("original_filename") or "").strip(),
        media_type=str(arguments.get("media_type") or "").strip(),
        title=str(arguments.get("title") or "").strip(),
        purpose=str(arguments.get("purpose") or "agent_output").strip(),
        visibility_scope=str(
            arguments.get("visibility_scope") or "course_teacher"
        ),
        source_agent_run_id=str(arguments.get("source_agent_run_id") or "")[:100]
        or grant.agent_run_id,
    )
    db.session.flush()
    return asset_to_dict(asset)


def _question_upsert(grant, arguments):
    questions = arguments.get("questions")
    if not isinstance(questions, list) or not questions or len(questions) > 100:
        raise ToolGatewayError(
            "questions must contain 1 to 100 canonical objects",
            400,
            "invalid_question_batch",
        )
    source_agent_run_id = (
        str(arguments.get("source_agent_run_id") or "")[:100]
        or grant.agent_run_id
    )
    items = []
    for payload in questions:
        if not isinstance(payload, dict):
            raise ToolGatewayError(
                "every question must be an object",
                400,
                "invalid_question_batch",
            )
        item = create_question(
            grant.course_id,
            grant.actor_user_id,
            {**payload, "source_agent_run_id": source_agent_run_id},
            source_type="agent",
        )
        if arguments.get("publish") is True:
            publish_question(item, grant.actor_user_id)
        items.append(question_to_dict(item, include_answer=True))
    return {"items": items}


def _paper_compose(grant, arguments):
    paper = compose_paper(
        grant.course_id,
        grant.actor_user_id,
        arguments,
    )
    return paper_to_dict(paper)


def _student_insight(grant, _arguments):
    rows = refresh_student_insights(grant.course_id, grant.actor_user_id)
    return {"items": [insight_to_dict(row) for row in rows]}


def _mock_exam(grant, arguments):
    return attempt_to_dict(
        create_mock_exam(grant.course_id, grant.actor_user_id, arguments)
    )


def _weakness(grant, _arguments):
    return weakness_to_dict(
        create_weakness_snapshot(grant.course_id, grant.actor_user_id)
    )


def _mind_map(grant, arguments):
    return mind_map_to_dict(
        create_mind_map(grant.course_id, grant.actor_user_id, arguments)
    )


DISPATCH = {
    "edu.course.list": _list_courses,
    "edu.course.members.list": _list_members,
    "edu.course.context.get": _course_context,
    "edu.question_bank.search": _question_search,
    "edu.knowledge.search": _knowledge_search,
    "edu.course.create": _create_course,
    "edu.course.members.import": _import_members,
    "edu.lesson.create": _create_lesson,
    "edu.courseware.create": _courseware_create,
    "edu.asset.attach": _attach_asset,
    "edu.question_bank.upsert": _question_upsert,
    "edu.paper.compose": _paper_compose,
    "edu.student_insight.refresh": _student_insight,
    "edu.mock_exam.create": _mock_exam,
    "edu.weakness.analyze": _weakness,
    "edu.mind_map.create": _mind_map,
}


def _error_parts(error):
    if isinstance(error, ToolGatewayError):
        return error.message, error.status_code, error.error_code
    if isinstance(error, (KnowledgeServiceError, LearningServiceError, AssetServiceError)):
        return error.message, error.status_code, error.error_code
    return str(error), 500, "tool_execution_failed"


def invoke_tool(
    *,
    raw_token,
    tool_name,
    arguments,
    idempotency_key=None,
    agent_id=None,
):
    grant = resolve_grant(raw_token)
    definition = _tool_record(tool_name)
    if tool_name not in (grant.allowed_tools or []):
        raise ToolGatewayError(
            "tool is not included in this run grant",
            403,
            "tool_not_granted",
        )
    if grant.actor_role not in definition["roles"]:
        raise ToolGatewayError(
            "tool is not available to the granted role",
            403,
            "tool_role_forbidden",
        )
    if not isinstance(arguments, dict):
        raise ToolGatewayError(
            "arguments must be an object",
            400,
            "invalid_tool_arguments",
        )
    forbidden = sorted(RESERVED_SCOPE_ARGUMENTS.intersection(arguments))
    if forbidden:
        raise ToolGatewayError(
            "actor and course scope are server-issued and cannot be arguments",
            400,
            "tool_scope_argument_forbidden",
        )
    write = definition["mode"] == "write"
    key = str(idempotency_key or "").strip()
    if write and (not key or len(key) > 120):
        raise ToolGatewayError(
            "write tools require an idempotency_key of at most 120 characters",
            400,
            "idempotency_key_required",
        )
    input_hash = _payload_hash(arguments)
    if key:
        existing = EducationToolCall.query.filter_by(
            grant_id=grant.id,
            tool_name=tool_name,
            idempotency_key=key,
        ).first()
        if existing:
            if existing.input_hash != input_hash:
                raise ToolGatewayError(
                    "idempotency_key was already used with different arguments",
                    409,
                    "idempotency_conflict",
                )
            if existing.status == "completed":
                return existing, existing.result_json or {}, True
            if existing.status == "failed":
                raise ToolGatewayError(
                    existing.error_message or "previous invocation failed",
                    409,
                    existing.error_code or "previous_invocation_failed",
                )
            raise ToolGatewayError(
                "an invocation with this idempotency_key is still running",
                409,
                "invocation_in_progress",
            )
    call = EducationToolCall(
        grant_id=grant.id,
        course_id=grant.course_id,
        actor_user_id=grant.actor_user_id,
        agent_id=str(agent_id or "")[:100] or None,
        tool_name=tool_name,
        idempotency_key=key or None,
        input_hash=input_hash,
        sanitized_input=_sanitize(arguments),
        status="running",
    )
    grant.last_used_at = datetime.utcnow()
    db.session.add(call)
    db.session.commit()

    try:
        result = DISPATCH[tool_name](grant, arguments)
        db.session.flush()
        call = EducationToolCall.query.get(call.id)
        call.result_json = result
        call.result_summary = _summary(result)
        call.status = "completed"
        call.completed_at = datetime.utcnow()
        db.session.commit()
        return call, result, False
    except Exception as error:
        db.session.rollback()
        message, status_code, error_code = _error_parts(error)
        call = EducationToolCall.query.get(call.id)
        if call:
            call.status = "failed"
            call.error_code = error_code
            call.error_message = str(message)[:500]
            call.completed_at = datetime.utcnow()
            db.session.commit()
        raise ToolGatewayError(message, status_code, error_code) from error
