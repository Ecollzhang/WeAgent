"""Membership-scoped Education content and teaching-loop API."""

import base64
import hashlib
import json
import os
from datetime import datetime
from io import BytesIO

from flask import Blueprint, Response, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import DataError
from werkzeug.utils import secure_filename

from .asset_models import EducationAsset
from .asset_service import (
    AssetServiceError,
    asset_to_dict,
    asset_storage_capacity_error,
    create_database_asset,
    validate_asset_access,
)
from .content_models import (
    Assignment,
    AssignmentContentVersion,
    AssignmentImportJob,
    CourseUnit,
    EducationContent,
    EducationContentVersion,
    EducationMaterial,
    Feedback,
    LearningEvent,
    Lesson,
    LessonActivity,
    PublishedLessonVersion,
    ReviewDraft,
    Submission,
    SubmissionReviewAnalysis,
    SubmissionVersion,
)
from .content_exporters import ContentExportError, export_content_bytes, export_pptx
from .course_context_service import build_courseware_context
from .document_extraction import DocumentExtractionError, extract_document_text
from .extensions import db
from .models import Course, CourseMemberProfile, CourseMembership
from .presentation_quality import inspect_pptx_bytes, inspect_slide_document
from .presentation_rendering import PresentationRenderError, render_pptx_pages


education_content_api = Blueprint("education_content_api", __name__)

SUBJECT_GENRES = {
    "high_school_english": {
        "narrative", "expository", "argumentative", "practical",
        "news", "biography", "literary",
    },
    "primary_chinese": {
        "narrative", "scenery", "expository", "fairy_tale", "fable",
        "poetry", "ancient_poetry", "practical", "composition",
    },
}
LEARNING_DOMAINS = {"reading", "writing", "integrated"}
LESSON_TYPES = {"reading", "writing", "reading_writing", "integrated"}
ACTIVITY_TYPES = {"resource", "reading", "presentation", "practice", "assignment", "writing"}
CONTENT_KINDS = {
    "lesson_plan", "rich_document", "slide_document", "assessment", "rubric",
    "teacher_feedback", "student_note", "learning_plan", "knowledge_card",
}
MATERIAL_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "html", "htm"}
STUDENT_PRIVATE_KEYS = {
    "answer", "answers", "answer_key", "correct_answer", "explanation",
    "common_mistakes", "rubric", "teacher_payload",
}
ASSIGNMENT_IMPORT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
SUBMISSION_REVIEW_PROMPT_VERSION = "review-v1"


def _student_safe_payload(value):
    if isinstance(value, list):
        return [_student_safe_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _student_safe_payload(item)
            for key, item in value.items()
            if key not in STUDENT_PRIVATE_KEYS and not key.startswith("teacher_")
        }
    return value


def _student_learning_outline(source):
    """Project a lesson plan into a small, student-safe learning contract."""
    source = source if isinstance(source, dict) else {}
    objectives = []
    for item in source.get("objectives") or []:
        if isinstance(item, str):
            objectives.append(item)
        elif isinstance(item, dict):
            projected = {
                key: item[key]
                for key in ("id", "description", "text", "objective", "title")
                if item.get(key) not in (None, "")
            }
            if projected:
                objectives.append(projected)
    stages = []
    for item in source.get("stages") or []:
        if not isinstance(item, dict):
            continue
        projected = {
            key: item[key]
            for key in (
                "id",
                "name",
                "title",
                "duration_minutes",
                "description",
                "student_activity",
                "activity",
                "task",
            )
            if item.get(key) not in (None, "")
        }
        if projected:
            stages.append(_student_safe_payload(projected))
    return {
        "learning_domain": source.get("learning_domain"),
        "text_genre_code": source.get("text_genre_code"),
        "lesson_type_code": source.get("lesson_type_code"),
        "duration_minutes": source.get("duration_minutes"),
        "objectives": objectives,
        "stages": stages,
    }


def _membership(course_id, user_id, role=None):
    query = CourseMembership.query.filter_by(
        course_id=course_id, user_id=user_id, status="active"
    )
    if role:
        query = query.filter_by(role=role)
    return query.first()


def _teacher_course(course_id, user_id):
    if not _membership(course_id, user_id, "teacher"):
        return None
    return Course.query.filter_by(id=course_id, status="active").first()


def _course_member(course_id, user_id):
    return _membership(course_id, user_id)


def _lesson_for_member(lesson_id, user_id, role=None):
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson or not _membership(lesson.course_id, user_id, role):
        return None
    return lesson


def _json_checksum(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event(course_id, actor, event_type, object_type, object_id, payload=None):
    db.session.add(
        LearningEvent(
            course_id=course_id,
            actor_user_id=actor,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            payload=payload or {},
        )
    )


def _unit_dict(unit):
    return {
        "id": unit.id, "course_id": unit.course_id, "title": unit.title,
        "position": unit.position, "status": unit.status,
    }


def _lesson_dict(lesson):
    return {
        "id": lesson.id, "course_id": lesson.course_id, "unit_id": lesson.unit_id,
        "title": lesson.title, "learning_domain": lesson.learning_domain,
        "theme_code": lesson.theme_code, "text_genre_code": lesson.text_genre_code,
        "lesson_type_code": lesson.lesson_type_code,
        "duration_minutes": lesson.duration_minutes, "position": lesson.position,
        "status": lesson.status,
        "current_published_version_id": lesson.current_published_version_id,
    }


def _content_dict(content):
    return {
        "id": content.id, "course_id": content.course_id, "lesson_id": content.lesson_id,
        "kind": content.kind, "owner_user_id": content.owner_user_id,
        "visibility_scope": content.visibility_scope,
        "current_version_id": content.current_version_id, "status": content.status,
    }


def _version_dict(version):
    return {
        "id": version.id, "content_id": version.content_id,
        "version_number": version.version_number, "schema_name": version.schema_name,
        "schema_version": version.schema_version, "source_json": version.source_json,
        "rendered_html": version.rendered_html,
        "parent_version_id": version.parent_version_id,
        "change_summary": version.change_summary, "checksum": version.checksum,
        "created_by_user_id": version.created_by_user_id,
        "created_at": version.created_at.isoformat(),
    }


def _material_dict(material):
    return {
        "id": material.id,
        "course_id": material.course_id,
        "lesson_id": material.lesson_id,
        "title": material.title,
        "original_filename": material.original_filename,
        "extension": material.extension,
        "mime_type": material.mime_type,
        "file_size": material.file_size,
        "asset_id": material.asset_id,
        "status": material.status,
        "download_url": f"/api/edu/materials/{material.id}/download",
        "created_at": material.created_at.isoformat(),
    }


def _validate_plan(lesson, source):
    required = {"subject_code", "learning_domain", "text_genre_code", "objectives", "stages"}
    if not isinstance(source, dict) or not required.issubset(source):
        return "lesson plan is missing required structured fields"
    if not isinstance(source["objectives"], list) or not source["objectives"]:
        return "lesson plan objectives are required"
    if not isinstance(source["stages"], list) or not source["stages"]:
        return "lesson plan stages are required"
    course = Course.query.get(lesson.course_id)
    if (
        source["subject_code"] != course.subject_code
        or source["learning_domain"] != lesson.learning_domain
        or source["text_genre_code"] != lesson.text_genre_code
    ):
        return "lesson plan template does not match lesson classification"
    return None


@education_content_api.post("/courses/<course_id>/units")
@jwt_required()
def create_unit(course_id):
    user_id = get_jwt_identity()
    if not _teacher_course(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    unit = CourseUnit(
        course_id=course_id, title=title, position=int(data.get("position") or 0)
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify(_unit_dict(unit)), 201


@education_content_api.post("/courses/<course_id>/lessons")
@jwt_required()
def create_lesson(course_id):
    user_id = get_jwt_identity()
    course = _teacher_course(course_id, user_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    data = request.get_json(silent=True) or {}
    domain = str(data.get("learning_domain") or "")
    genre = str(data.get("text_genre_code") or "")
    lesson_type = str(data.get("lesson_type_code") or "")
    if not str(data.get("title") or "").strip():
        return jsonify({"error": "title is required"}), 400
    if (
        domain not in LEARNING_DOMAINS
        or genre not in SUBJECT_GENRES.get(course.subject_code, set())
        or lesson_type not in LESSON_TYPES
    ):
        return jsonify({"error": "lesson classification is not supported by subject template"}), 400
    unit_id = data.get("unit_id")
    if unit_id and not CourseUnit.query.filter_by(id=unit_id, course_id=course_id).first():
        return jsonify({"error": "unit not found"}), 404
    try:
        duration = int(data.get("duration_minutes") or 0)
        position = int(data.get("position") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "duration and position must be integers"}), 400
    if duration < 1 or duration > 600:
        return jsonify({"error": "invalid duration_minutes"}), 400
    lesson = Lesson(
        course_id=course_id, unit_id=unit_id, title=str(data["title"]).strip(),
        learning_domain=domain, theme_code=str(data.get("theme_code") or "").strip(),
        text_genre_code=genre, lesson_type_code=lesson_type,
        duration_minutes=duration, position=position,
    )
    db.session.add(lesson)
    db.session.commit()
    return jsonify(_lesson_dict(lesson)), 201


@education_content_api.get("/courses/<course_id>/structure")
@jwt_required()
def get_course_structure(course_id):
    user_id = get_jwt_identity()
    membership = _course_member(course_id, user_id)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    lesson_query = Lesson.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        lesson_query = lesson_query.filter_by(status="published")
    lessons = lesson_query.order_by(Lesson.position.asc(), Lesson.created_at.asc()).all()
    lessons_by_unit = {}
    for lesson in lessons:
        lessons_by_unit.setdefault(lesson.unit_id, []).append(_lesson_dict(lesson))
    units = CourseUnit.query.filter_by(
        course_id=course_id, status="active"
    ).order_by(CourseUnit.position.asc(), CourseUnit.created_at.asc()).all()
    return jsonify(
        {
            "course_id": course_id,
            "units": [
                {**_unit_dict(unit), "lessons": lessons_by_unit.get(unit.id, [])}
                for unit in units
            ],
            "ungrouped_lessons": lessons_by_unit.get(None, []),
        }
    )


@education_content_api.get("/lessons/<lesson_id>")
@jwt_required()
def get_lesson(lesson_id):
    user_id = get_jwt_identity()
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    membership = _membership(lesson.course_id, user_id)
    if not membership or (
        membership.role != "teacher" and lesson.status != "published"
    ):
        return jsonify({"error": "lesson not found"}), 404
    activities = LessonActivity.query.filter_by(lesson_id=lesson.id).order_by(
        LessonActivity.position.asc()
    ).all()
    if membership.role != "teacher":
        activities = [row for row in activities if row.status == "published"]
    result = _lesson_dict(lesson)
    result["activities"] = [
        {
            "id": row.id,
            "activity_type": row.activity_type,
            "title": row.title,
            "position": row.position,
            "status": row.status,
            **(row.student_payload or {}),
            **({"teacher_payload": row.teacher_payload} if membership.role == "teacher" else {}),
        }
        for row in activities
    ]
    return jsonify(result)


@education_content_api.get("/lessons/<lesson_id>/courseware-context")
@jwt_required()
def get_courseware_context(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    context = build_courseware_context(lesson.course_id, lesson.id)
    if not context:
        return jsonify({"error": "lesson not found"}), 404
    return jsonify(context)


@education_content_api.post("/lessons/<lesson_id>/activities")
@jwt_required()
def create_activity(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    activity_type = str(data.get("activity_type") or "")
    title = str(data.get("title") or "").strip()
    if activity_type not in ACTIVITY_TYPES or not title:
        return jsonify({"error": "valid activity_type and title are required"}), 400
    activity = LessonActivity(
        course_id=lesson.course_id, lesson_id=lesson.id, activity_type=activity_type,
        title=title, position=int(data.get("position") or 0),
        content_version_id=data.get("content_version_id"),
        student_payload=_student_safe_payload(data.get("student_payload") or {}),
        teacher_payload=data.get("teacher_payload") or {},
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({
        "id": activity.id, "lesson_id": activity.lesson_id,
        "activity_type": activity.activity_type, "title": activity.title,
        "position": activity.position, "content_version_id": activity.content_version_id,
        "student_payload": activity.student_payload, "status": activity.status,
    }), 201


@education_content_api.post("/lessons/<lesson_id>/materials")
@jwt_required()
def upload_material(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "file is required"}), 400
    filename = secure_filename(uploaded.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in MATERIAL_EXTENSIONS:
        return jsonify({
            "error": "unsupported material type",
            "supported_extensions": sorted(MATERIAL_EXTENSIONS),
        }), 400
    content = uploaded.read()
    max_bytes = int(current_app.config.get("EDUCATION_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
    if not content or len(content) > max_bytes:
        return jsonify({"error": "material is empty or exceeds the upload limit"}), 400
    try:
        asset = create_database_asset(
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            actor_user_id=user_id,
            content=content,
            original_filename=uploaded.filename,
            media_type=uploaded.mimetype or "application/octet-stream",
            title=str(request.form.get("title") or uploaded.filename).strip(),
            purpose="lesson_material",
            visibility_scope="course_teacher",
        )
    except AssetServiceError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    except DataError:
        db.session.rollback()
        error = asset_storage_capacity_error()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    material = EducationMaterial(
        course_id=lesson.course_id,
        lesson_id=lesson.id,
        owner_user_id=user_id,
        title=str(request.form.get("title") or uploaded.filename).strip(),
        original_filename=uploaded.filename,
        extension=extension,
        mime_type=uploaded.mimetype or "application/octet-stream",
        # Empty string keeps inserts compatible with pre-migration schemas whose
        # legacy path column was NOT NULL; ``asset_id`` is authoritative.
        storage_path="",
        asset_id=asset.id,
        file_size=len(content),
    )
    db.session.add(material)
    db.session.commit()
    return jsonify(_material_dict(material)), 201


@education_content_api.get("/lessons/<lesson_id>/materials")
@jwt_required()
def list_materials(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id)
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    membership = _membership(lesson.course_id, user_id)
    query = EducationMaterial.query.filter_by(lesson_id=lesson.id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    rows = query.order_by(EducationMaterial.created_at.asc()).all()
    return jsonify({"items": [_material_dict(row) for row in rows]})


@education_content_api.get("/materials/<material_id>/download")
@jwt_required()
def download_material(material_id):
    user_id = get_jwt_identity()
    material = EducationMaterial.query.filter_by(id=material_id).first()
    if not material:
        return jsonify({"error": "material not found"}), 404
    membership = _membership(material.course_id, user_id)
    if not membership or (membership.role != "teacher" and material.status != "published"):
        return jsonify({"error": "material not found"}), 404
    if material.asset_id:
        asset = EducationAsset.query.filter_by(id=material.asset_id).first()
        if not asset:
            return jsonify({"error": "material file is unavailable"}), 404
        try:
            validate_asset_access(asset, user_id)
        except AssetServiceError:
            return jsonify({"error": "material not found"}), 404
        return send_file(
            BytesIO(asset.blob_bytes),
            mimetype=asset.media_type,
            as_attachment=True,
            download_name=asset.original_filename,
        )
    if not material.storage_path or not os.path.isfile(material.storage_path):
        return jsonify({"error": "material file is unavailable"}), 404
    return send_file(
        material.storage_path,
        mimetype=material.mime_type,
        as_attachment=True,
        download_name=material.original_filename,
    )


def _create_version(content, data, user_id):
    source = data.get("source_json")
    lesson = Lesson.query.get(content.lesson_id) if content.lesson_id else None
    if content.kind == "lesson_plan":
        error = _validate_plan(lesson, source)
        if error:
            return None, error
    if not isinstance(source, dict):
        return None, "source_json must be an object"
    latest = (
        EducationContentVersion.query.filter_by(content_id=content.id)
        .order_by(EducationContentVersion.version_number.desc()).first()
    )
    version = EducationContentVersion(
        content_id=content.id, version_number=(latest.version_number + 1 if latest else 1),
        schema_name=str(data.get("schema_name") or "").strip(),
        schema_version=str(data.get("schema_version") or "1.0"),
        source_json=source, rendered_html=data.get("rendered_html"),
        parent_version_id=latest.id if latest else None,
        change_summary=str(data.get("change_summary") or ""),
        created_by_user_id=user_id, source_agent_run_id=data.get("source_agent_run_id"),
        checksum=_json_checksum(source),
    )
    if not version.schema_name:
        return None, "schema_name is required"
    db.session.add(version)
    db.session.flush()
    content.current_version_id = version.id
    return version, None


@education_content_api.post("/lessons/<lesson_id>/contents")
@jwt_required()
def create_content(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "")
    if kind not in CONTENT_KINDS:
        return jsonify({"error": "unsupported content kind"}), 400
    content = EducationContent(
        course_id=lesson.course_id, lesson_id=lesson.id, kind=kind,
        owner_user_id=user_id,
        visibility_scope=str(data.get("visibility_scope") or "course_teacher"),
    )
    db.session.add(content)
    version, error = _create_version(content, data, user_id)
    if error:
        db.session.rollback()
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify({"content": _content_dict(content), "version": _version_dict(version)}), 201


@education_content_api.get("/lessons/<lesson_id>/contents")
@jwt_required()
def list_lesson_contents(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    rows = EducationContent.query.filter_by(
        lesson_id=lesson.id
    ).order_by(EducationContent.created_at.asc()).all()
    return jsonify({"items": [_content_dict(row) for row in rows]})


@education_content_api.post("/contents/<content_id>/versions")
@jwt_required()
def create_content_version(content_id):
    user_id = get_jwt_identity()
    content = EducationContent.query.filter_by(id=content_id).first()
    if not content or not _membership(content.course_id, user_id, "teacher"):
        return jsonify({"error": "content not found"}), 404
    version, error = _create_version(content, request.get_json(silent=True) or {}, user_id)
    if error:
        db.session.rollback()
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify({"content": _content_dict(content), "version": _version_dict(version)}), 201


@education_content_api.get("/contents/<content_id>/versions")
@jwt_required()
def list_content_versions(content_id):
    user_id = get_jwt_identity()
    content = EducationContent.query.filter_by(id=content_id).first()
    if not content or not _membership(content.course_id, user_id, "teacher"):
        return jsonify({"error": "content not found"}), 404
    versions = EducationContentVersion.query.filter_by(
        content_id=content.id
    ).order_by(EducationContentVersion.version_number.asc()).all()
    return jsonify({"items": [_version_dict(row) for row in versions]})


@education_content_api.get("/contents/<content_id>/visual-qa")
@jwt_required()
def inspect_content_visual_quality(content_id):
    """Inspect both the durable SlideDocument and its current PPTX rendering."""
    user_id = get_jwt_identity()
    content = EducationContent.query.filter_by(id=content_id).first()
    if not content or not _membership(content.course_id, user_id, "teacher"):
        return jsonify({"error": "content not found"}), 404
    if content.kind != "slide_document":
        return jsonify({"error": "visual QA is only available for slide documents"}), 400
    version = EducationContentVersion.query.filter_by(
        id=content.current_version_id,
        content_id=content.id,
    ).first()
    if not version:
        return jsonify({"error": "content version not found"}), 404
    lesson = (
        Lesson.query.filter_by(id=content.lesson_id).first()
        if content.lesson_id
        else None
    )
    source_report = inspect_slide_document(version.source_json or {})
    try:
        pptx_payload = export_pptx(
            version.source_json or {},
            lesson.title if lesson else f"education-content-{content.id}",
        )
        rendered_report = inspect_pptx_bytes(pptx_payload)
        rendered_pages = render_pptx_pages(pptx_payload)
    except ContentExportError as error:
        return jsonify(
            {
                "error": str(error),
                "adapter_status": "unavailable",
                "source": source_report,
            }
        ), 424
    except PresentationRenderError as error:
        return jsonify(
            {
                "error": str(error),
                "adapter_status": "unavailable",
                "render_adapter_status": "unavailable",
                "source": source_report,
                "rendered_pptx": rendered_report,
            }
        ), 424
    status = (
        "failed"
        if "failed" in {source_report["status"], rendered_report["status"]}
        else (
            "warning"
            if "warning" in {source_report["status"], rendered_report["status"]}
            else "passed"
        )
    )
    source_slides = source_report["slides"]
    rendered_slide_reports = rendered_report.get("slides") or []
    cover_offset = 1 if len(rendered_pages) == len(source_slides) + 1 else 0
    rendered_page_payloads = []
    for page in rendered_pages:
        page_number = int(page["number"])
        source_index = page_number - 1 - cover_offset
        source_slide = (
            source_slides[source_index]
            if 0 <= source_index < len(source_slides)
            else None
        )
        package_slide = (
            rendered_slide_reports[page_number - 1]
            if 0 <= page_number - 1 < len(rendered_slide_reports)
            else {}
        )
        findings = []
        if source_slide:
            findings.extend(source_slide.get("findings") or [])
        findings.extend(package_slide.get("findings") or [])
        page_statuses = {
            str((source_slide or {}).get("status") or "passed"),
            str(package_slide.get("status") or "passed"),
        }
        page_status = (
            "failed"
            if "failed" in page_statuses
            else ("warning" if "warning" in page_statuses else "passed")
        )
        rendered_page_payloads.append(
            {
                "id": (
                    str(source_slide.get("id"))
                    if source_slide
                    else f"rendered-page-{page_number}"
                ),
                "number": page_number,
                "title": (
                    str(source_slide.get("title"))
                    if source_slide
                    else str((version.source_json or {}).get("title") or "课件封面")
                ),
                "status": page_status,
                "findings": findings,
                "width": page["width"],
                "height": page["height"],
                "engine": page["engine"],
                "preview_data_url": (
                    "data:image/png;base64,"
                    + base64.b64encode(page["content"]).decode("ascii")
                ),
            }
        )
    return jsonify(
        {
            "status": status,
            "content_id": content.id,
            "version_id": version.id,
            "version_number": version.version_number,
            "theme_style": source_report["theme_style"],
            "theme_label": source_report["theme_label"],
            "slide_count": len(rendered_page_payloads),
            "source_slide_count": source_report["slide_count"],
            "slides": source_report["slides"],
            "findings": source_report["findings"],
            "rendered_pptx": rendered_report,
            "render_adapter_status": "ready",
            "rendered_pages": rendered_page_payloads,
        }
    )


@education_content_api.get("/contents/<content_id>/export")
@jwt_required()
def export_content(content_id):
    """Export the current durable source as JSON, HTML, Office, or PDF."""
    user_id = get_jwt_identity()
    content = EducationContent.query.filter_by(id=content_id).first()
    if not content or not _membership(content.course_id, user_id, "teacher"):
        return jsonify({"error": "content not found"}), 404
    version = EducationContentVersion.query.filter_by(
        id=content.current_version_id,
        content_id=content.id,
    ).first()
    if not version:
        return jsonify({"error": "content version not found"}), 404

    export_format = str(request.args.get("format") or "json").strip().lower()
    filename_base = f"education-content-{content.id}"
    if export_format == "json":
        body = json.dumps(
            {
                "content": _content_dict(content),
                "version": version.version_number,
                "schema_name": version.schema_name,
                "schema_version": version.schema_version,
                "source_json": version.source_json,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return Response(
            body,
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"'
            },
        )
    if export_format == "html":
        if not version.rendered_html:
            return jsonify(
                {
                    "error": "rendered HTML is not available",
                    "fallback_formats": ["json"],
                }
            ), 409
        return Response(
            version.rendered_html,
            mimetype="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.html"'
            },
        )
    if export_format in {"pptx", "docx", "pdf"}:
        lesson = (
            Lesson.query.filter_by(id=content.lesson_id).first()
            if content.lesson_id
            else None
        )
        try:
            body, mimetype = export_content_bytes(
                export_format,
                version.source_json or {},
                lesson.title if lesson else filename_base,
            )
        except ContentExportError as error:
            return jsonify(
                {
                    "error": str(error),
                    "adapter_status": "unavailable",
                    "fallback_formats": ["html", "json"],
                }
            ), 424
        return send_file(
            BytesIO(body),
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{filename_base}.{export_format}",
            max_age=0,
        )
    return jsonify(
        {
            "error": "unsupported export format",
            "supported_formats": ["json", "html", "pptx", "docx", "pdf"],
        }
    ), 400


def _publication_dict(publication, include_teacher=False):
    result = {
        "id": publication.id, "lesson_id": publication.lesson_id,
        "version_number": publication.version_number,
        "lesson_plan_version_id": publication.lesson_plan_version_id,
        "student_release_manifest": publication.student_release_manifest,
        "published_by": publication.published_by,
        "published_at": publication.published_at.isoformat(),
        "status": publication.status,
    }
    if include_teacher:
        result["teacher_evaluation_manifest"] = publication.teacher_evaluation_manifest
    return result


@education_content_api.post("/lessons/<lesson_id>/publish")
@jwt_required()
def publish_lesson(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    key = str(request.headers.get("Idempotency-Key") or "").strip()
    if not key:
        return jsonify({"error": "Idempotency-Key is required"}), 400
    existing = PublishedLessonVersion.query.filter_by(
        lesson_id=lesson_id, idempotency_key=key
    ).first()
    if existing:
        return jsonify(_publication_dict(existing, include_teacher=True))
    activities = LessonActivity.query.filter_by(
        lesson_id=lesson.id, status="draft"
    ).order_by(LessonActivity.position.asc()).all()
    plan = (
        db.session.query(EducationContentVersion)
        .join(EducationContent, EducationContent.id == EducationContentVersion.content_id)
        .filter(
            EducationContent.lesson_id == lesson.id,
            EducationContent.kind == "lesson_plan",
            EducationContent.current_version_id == EducationContentVersion.id,
        ).first()
    )
    if not plan:
        return jsonify({"error": "lesson requires a current lesson plan"}), 400
    student_contents = (
        db.session.query(EducationContent, EducationContentVersion)
        .join(
            EducationContentVersion,
            EducationContent.current_version_id == EducationContentVersion.id,
        )
        .filter(
            EducationContent.lesson_id == lesson.id,
            EducationContent.kind != "lesson_plan",
            EducationContent.visibility_scope == "course_students",
        )
        .order_by(EducationContent.created_at.asc())
        .all()
    )
    uploaded_materials = EducationMaterial.query.filter(
        EducationMaterial.lesson_id == lesson.id,
        EducationMaterial.status.in_(("draft", "published")),
    ).order_by(EducationMaterial.created_at.asc()).all()
    if not activities and not student_contents and not uploaded_materials:
        return jsonify({
            "error": (
                "lesson requires student courseware, an uploaded material, "
                "or at least one learning activity"
            )
        }), 400
    student_activities = [
        {
            "id": row.id, "type": row.activity_type, "title": row.title,
            "position": row.position, **(row.student_payload or {}),
        }
        for row in activities
    ]
    teacher_activities = [
        {"id": row.id, **(row.teacher_payload or {})} for row in activities
    ]
    previous = (
        PublishedLessonVersion.query.filter_by(lesson_id=lesson.id)
        .order_by(PublishedLessonVersion.version_number.desc()).first()
    )
    PublishedLessonVersion.query.filter_by(
        lesson_id=lesson.id, status="active"
    ).update({"status": "withdrawn"})
    publication = PublishedLessonVersion(
        lesson_id=lesson.id,
        version_number=(previous.version_number + 1 if previous else 1),
        lesson_plan_version_id=plan.id,
        student_release_manifest={
            "lesson": {
                "id": lesson.id, "title": lesson.title,
                "learning_domain": lesson.learning_domain,
            },
            "learning_outline": _student_learning_outline(plan.source_json),
            "activities": student_activities,
            "materials": [
                {
                    "content_id": content.id,
                    "version_id": version.id,
                    "kind": content.kind,
                    "schema_name": version.schema_name,
                    "source_json": version.source_json,
                    "rendered_html": version.rendered_html,
                }
                for content, version in student_contents
            ] + [
                {"kind": "file", **_material_dict(material)}
                for material in uploaded_materials
            ],
        },
        teacher_evaluation_manifest={"activities": teacher_activities},
        idempotency_key=key, published_by=user_id,
    )
    db.session.add(publication)
    db.session.flush()
    lesson.status = "published"
    lesson.current_published_version_id = publication.id
    for row in activities:
        row.status = "published"
    for material in uploaded_materials:
        material.status = "published"
        if material.asset_id:
            EducationAsset.query.filter_by(id=material.asset_id).update(
                {"visibility_scope": "course_published"}
            )
    _event(lesson.course_id, user_id, "LessonPublished", "lesson", lesson.id)
    db.session.commit()
    return jsonify(_publication_dict(publication, include_teacher=True)), 201


@education_content_api.get("/lessons/<lesson_id>/release")
@jwt_required()
def get_student_release(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id)
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    publication = PublishedLessonVersion.query.filter_by(
        id=lesson.current_published_version_id, status="active"
    ).first()
    if not publication:
        return jsonify({"error": "published lesson not found"}), 404
    _event(lesson.course_id, user_id, "LessonViewed", "lesson", lesson.id)
    db.session.commit()
    return jsonify(_publication_dict(publication, include_teacher=False))


@education_content_api.get("/lessons/<lesson_id>/publication")
@jwt_required()
def get_teacher_publication(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    publication = PublishedLessonVersion.query.filter_by(
        id=lesson.current_published_version_id, status="active"
    ).first()
    if not publication:
        return jsonify({"error": "published lesson not found"}), 404
    return jsonify(_publication_dict(publication, include_teacher=True))


def _assets_for_ids(asset_ids, course_id):
    ordered_ids = [str(item) for item in (asset_ids or []) if item]
    if not ordered_ids:
        return []
    rows = EducationAsset.query.filter(
        EducationAsset.course_id == course_id,
        EducationAsset.status == "active",
        EducationAsset.id.in_(ordered_ids),
    ).all()
    by_id = {row.id: row for row in rows}
    return [by_id[item] for item in ordered_ids if item in by_id]


def _assignment_version_dict(version):
    if not version:
        return None
    return {
        "id": version.id,
        "version_number": version.version_number,
        "created_by": version.created_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


def _assignment_version(assignment, version_id):
    if not version_id:
        return None
    return AssignmentContentVersion.query.filter_by(
        id=version_id, assignment_id=assignment.id
    ).first()


def _new_assignment_version(assignment, actor_user_id, version_number=None, **overrides):
    if version_number is None:
        latest = (
            AssignmentContentVersion.query.filter_by(assignment_id=assignment.id)
            .order_by(AssignmentContentVersion.version_number.desc())
            .first()
        )
        version_number = (latest.version_number if latest else 0) + 1
    values = {
        "title": assignment.title,
        "kind": assignment.kind,
        "instruction_json": assignment.instruction_json,
        "evaluation_json": assignment.evaluation_json or {},
        "source_asset_ids": assignment.source_asset_ids or [],
        "max_score": assignment.max_score,
        "max_attempts": assignment.max_attempts,
        "allow_revision_after_feedback": assignment.allow_revision_after_feedback,
    }
    values.update(overrides)
    version = AssignmentContentVersion(
        assignment_id=assignment.id,
        version_number=version_number,
        created_by=actor_user_id,
        **values,
    )
    db.session.add(version)
    db.session.flush()
    assignment.current_version_id = version.id
    return version


def _ensure_assignment_version(assignment, actor_user_id="system"):
    current = _assignment_version(assignment, assignment.current_version_id)
    if current:
        return current
    current = _new_assignment_version(assignment, actor_user_id, version_number=1)
    if assignment.status == "published":
        current.published_at = assignment.published_at or datetime.utcnow()
        assignment.published_version_id = current.id
    return current


def _apply_assignment_version(assignment, version):
    assignment.title = version.title
    assignment.kind = version.kind
    assignment.instruction_json = version.instruction_json
    assignment.evaluation_json = version.evaluation_json or {}
    assignment.source_asset_ids = version.source_asset_ids or []
    assignment.max_score = version.max_score
    assignment.max_attempts = version.max_attempts
    assignment.allow_revision_after_feedback = version.allow_revision_after_feedback


def _assignment_dict(assignment, include_evaluation=False, version=None):
    current_version = _assignment_version(assignment, assignment.current_version_id)
    published_version = _assignment_version(assignment, assignment.published_version_id)
    version = version or current_version
    payload = version or assignment
    source_assets = _assets_for_ids(
        payload.source_asset_ids,
        assignment.course_id,
    )
    result = {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "lesson_id": assignment.lesson_id,
        "title": payload.title,
        "kind": payload.kind,
        "instruction_json": payload.instruction_json,
        "source_assets": [asset_to_dict(asset) for asset in source_assets],
        "max_score": payload.max_score,
        "max_attempts": payload.max_attempts,
        "allow_revision_after_feedback": payload.allow_revision_after_feedback,
        "status": assignment.status,
        "current_version": _assignment_version_dict(current_version),
        "published_version": _assignment_version_dict(published_version),
        "has_unpublished_changes": bool(
            current_version
            and (not published_version or current_version.id != published_version.id)
        ),
        "published_at": (
            assignment.published_at.isoformat() if assignment.published_at else None
        ),
    }
    if include_evaluation:
        result["evaluation_json"] = payload.evaluation_json
    return result


def _assignment_import_dict(job):
    asset = EducationAsset.query.filter_by(id=job.source_asset_id).first()
    return {
        "id": job.id,
        "course_id": job.course_id,
        "lesson_id": job.lesson_id,
        "mode": job.mode,
        "status": job.status,
        "extractor_code": job.extractor_code,
        "extracted_text": job.extracted_text or "",
        "draft_json": job.draft_json or {},
        "warnings": job.warnings or [],
        "error_summary": job.error_summary,
        "source_asset": asset_to_dict(asset) if asset else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _assignment_import_for_teacher(job_id, user_id):
    job = AssignmentImportJob.query.filter_by(id=job_id).first()
    if not job or not _membership(job.course_id, user_id, "teacher"):
        return None
    return job


@education_content_api.post("/courses/<course_id>/assignment-imports")
@jwt_required()
def create_assignment_import(course_id):
    user_id = get_jwt_identity()
    if not _membership(course_id, user_id, "teacher"):
        return jsonify({"error": "course not found"}), 404
    lesson_id = str(request.form.get("lesson_id") or "").strip()
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first()
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    mode = str(request.form.get("mode") or "attachment").strip()
    if mode not in {"attachment", "editable"}:
        return jsonify({"error": "mode must be attachment or editable"}), 400
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "file is required", "error_code": "file_required"}), 400
    extension = os.path.splitext(uploaded.filename)[1].lower()
    media_type = ASSIGNMENT_IMPORT_EXTENSIONS.get(extension)
    if not media_type:
        return jsonify(
            {
                "error": "only PDF, PNG, JPG, and JPEG files are supported",
                "error_code": "unsupported_document_type",
            }
        ), 400
    content = uploaded.read()
    max_bytes = int(
        current_app.config.get("EDUCATION_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
    )
    if not content or len(content) > max_bytes:
        return jsonify(
            {
                "error": "file is empty or exceeds the upload limit",
                "error_code": "asset_size_invalid",
            }
        ), 400
    filename = secure_filename(uploaded.filename) or f"assignment-source{extension}"
    try:
        asset = create_database_asset(
            course_id=course_id,
            lesson_id=lesson.id,
            actor_user_id=user_id,
            content=content,
            original_filename=filename,
            media_type=media_type,
            title=str(request.form.get("title") or uploaded.filename).strip(),
            purpose="assignment_source",
            visibility_scope="course_teacher",
        )
        draft = {}
        status = "uploaded"
        if mode == "attachment":
            status = "ready"
            draft = {
                "title": os.path.splitext(uploaded.filename)[0],
                "instruction_json": {"text": "请完成并提交附件中的作业。"},
                "source_asset_ids": [asset.id],
            }
        job = AssignmentImportJob(
            course_id=course_id,
            lesson_id=lesson.id,
            source_asset_id=asset.id,
            requested_by=user_id,
            mode=mode,
            status=status,
            draft_json=draft,
        )
        db.session.add(job)
        db.session.commit()
    except AssetServiceError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    except DataError:
        db.session.rollback()
        error = asset_storage_capacity_error()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    return jsonify(_assignment_import_dict(job)), 201


@education_content_api.get("/assignment-imports/<job_id>")
@jwt_required()
def get_assignment_import(job_id):
    job = _assignment_import_for_teacher(job_id, get_jwt_identity())
    if not job:
        return jsonify({"error": "assignment import not found"}), 404
    return jsonify(_assignment_import_dict(job))


@education_content_api.post("/assignment-imports/<job_id>/process")
@jwt_required()
def process_assignment_import(job_id):
    job = _assignment_import_for_teacher(job_id, get_jwt_identity())
    if not job:
        return jsonify({"error": "assignment import not found"}), 404
    if job.mode != "editable":
        return jsonify(_assignment_import_dict(job))
    if job.status == "review_required":
        return jsonify(_assignment_import_dict(job))
    asset = EducationAsset.query.filter_by(
        id=job.source_asset_id,
        course_id=job.course_id,
        status="active",
    ).first()
    if not asset:
        return jsonify({"error": "assignment source is unavailable"}), 404
    job.status = "extracting"
    job.error_summary = None
    db.session.commit()
    try:
        text, extractor_code, warnings = extract_document_text(
            bytes(asset.blob_bytes),
            asset.media_type,
        )
    except DocumentExtractionError as error:
        job.status = "failed"
        job.error_summary = error.message
        job.warnings = [{"code": error.error_code, "message": error.message}]
        db.session.commit()
        return jsonify(_assignment_import_dict(job)), 422
    job.status = "review_required"
    job.extractor_code = extractor_code
    job.extracted_text = text
    job.warnings = warnings
    job.draft_json = {
        "title": os.path.splitext(asset.original_filename)[0],
        "instruction_json": {"text": text},
        "source_asset_ids": [asset.id],
    }
    db.session.commit()
    return jsonify(_assignment_import_dict(job))


def _submission_dict(submission):
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "student_user_id": submission.student_user_id,
        "status": submission.status,
        "current_version_id": submission.current_version_id,
        "attempt_count": submission.attempt_count,
        "submitted_at": (
            submission.submitted_at.isoformat() if submission.submitted_at else None
        ),
        "final_score": submission.final_score,
        "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
    }


def _submission_version_dict(version):
    return {
        "id": version.id,
        "submission_id": version.submission_id,
        "version_number": version.version_number,
        "answer_json": version.answer_json,
        "artifact_ids": version.artifact_ids,
        "submitted_at": version.submitted_at.isoformat(),
        "source_version_id": version.source_version_id,
        "checksum": version.checksum,
    }


def _assignment_for_member(assignment_id, user_id, role=None):
    assignment = Assignment.query.filter_by(id=assignment_id).first()
    if not assignment or not _membership(assignment.course_id, user_id, role):
        return None
    return assignment


@education_content_api.get("/assignments/<assignment_id>")
@jwt_required()
def get_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id)
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    membership = _membership(assignment.course_id, user_id)
    if membership.role != "teacher" and assignment.status != "published":
        return jsonify({"error": "assignment not found"}), 404
    current = _ensure_assignment_version(assignment, user_id)
    published = _assignment_version(assignment, assignment.published_version_id)
    if membership.role != "teacher" and not published:
        return jsonify({"error": "assignment not found"}), 404
    if db.session.is_modified(assignment):
        db.session.commit()
    return jsonify(
        _assignment_dict(
            assignment,
            include_evaluation=membership.role == "teacher",
            version=current if membership.role == "teacher" else published,
        )
    )


@education_content_api.post("/lessons/<lesson_id>/assignments")
@jwt_required()
def create_assignment(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    kind = str(data.get("kind") or "")
    instruction = data.get("instruction_json")
    evaluation = data.get("evaluation_json") or {}
    if not title or kind not in {"quiz", "writing", "mixed"}:
        return jsonify({"error": "valid title and kind are required"}), 400
    if not isinstance(instruction, dict) or not instruction:
        return jsonify({"error": "instruction_json is required"}), 400
    if not isinstance(evaluation, dict):
        return jsonify({"error": "evaluation_json must be an object"}), 400
    source_asset_ids = data.get("source_asset_ids") or []
    if not isinstance(source_asset_ids, list) or len(source_asset_ids) > 20:
        return jsonify({"error": "source_asset_ids must be a list of at most 20 items"}), 400
    source_asset_ids = list(dict.fromkeys(str(item) for item in source_asset_ids if item))
    source_assets = _assets_for_ids(source_asset_ids, lesson.course_id)
    if len(source_assets) != len(source_asset_ids):
        return jsonify({"error": "one or more source assets are unavailable"}), 400
    rubric = evaluation.get("rubric")
    inferred_max_score = None
    if isinstance(rubric, dict) and rubric:
        try:
            inferred_max_score = sum(float(value) for value in rubric.values())
        except (TypeError, ValueError):
            inferred_max_score = None
    try:
        max_score = float(
            data.get("max_score")
            or evaluation.get("max_score")
            or inferred_max_score
            or 100
        )
    except (TypeError, ValueError):
        return jsonify({"error": "max_score must be numeric"}), 400
    if not 0 < max_score <= 10000:
        return jsonify({"error": "invalid max_score"}), 400
    try:
        max_attempts = int(data.get("max_attempts", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "max_attempts must be an integer"}), 400
    if not 1 <= max_attempts <= 20:
        return jsonify({"error": "invalid max_attempts"}), 400
    assignment = Assignment(
        course_id=lesson.course_id,
        lesson_id=lesson.id,
        title=title,
        kind=kind,
        instruction_json=instruction,
        evaluation_json=evaluation,
        source_asset_ids=source_asset_ids,
        max_score=max_score,
        max_attempts=max_attempts,
        allow_revision_after_feedback=bool(
            data.get("allow_revision_after_feedback", True)
        ),
    )
    db.session.add(assignment)
    db.session.flush()
    _new_assignment_version(assignment, user_id, version_number=1)
    db.session.commit()
    return jsonify(_assignment_dict(assignment, include_evaluation=False)), 201


@education_content_api.patch("/assignments/<assignment_id>")
@jwt_required()
def update_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "teacher")
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    data = request.get_json(silent=True) or {}
    current = _ensure_assignment_version(assignment, user_id)
    expected_version_id = str(data.get("current_version_id") or "").strip()
    if expected_version_id and expected_version_id != current.id:
        db.session.rollback()
        return jsonify(
            {
                "error": "assignment changed in another session",
                "error_code": "assignment_version_conflict",
                "current_version_id": current.id,
            }
        ), 409

    title = str(data.get("title", current.title) or "").strip()
    kind = str(data.get("kind", current.kind) or "").strip()
    instruction = data.get("instruction_json", current.instruction_json)
    evaluation = data.get("evaluation_json", current.evaluation_json) or {}
    if not title or len(title) > 200 or kind not in {"quiz", "writing", "mixed"}:
        return jsonify({"error": "valid title and kind are required"}), 400
    if not isinstance(instruction, dict) or not instruction:
        return jsonify({"error": "instruction_json is required"}), 400
    if not isinstance(evaluation, dict):
        return jsonify({"error": "evaluation_json must be an object"}), 400
    source_asset_ids = data.get("source_asset_ids", current.source_asset_ids) or []
    if not isinstance(source_asset_ids, list) or len(source_asset_ids) > 20:
        return jsonify({"error": "source_asset_ids must be a list of at most 20 items"}), 400
    source_asset_ids = list(dict.fromkeys(str(item) for item in source_asset_ids if item))
    if len(_assets_for_ids(source_asset_ids, assignment.course_id)) != len(source_asset_ids):
        return jsonify({"error": "one or more source assets are unavailable"}), 400
    try:
        max_score = float(data.get("max_score", current.max_score))
        max_attempts = int(data.get("max_attempts", current.max_attempts))
    except (TypeError, ValueError):
        return jsonify({"error": "score and attempts must be numeric"}), 400
    if not 0 < max_score <= 10000 or not 1 <= max_attempts <= 20:
        return jsonify({"error": "invalid score or attempts"}), 400
    values = {
        "title": title,
        "kind": kind,
        "instruction_json": instruction,
        "evaluation_json": evaluation,
        "source_asset_ids": source_asset_ids,
        "max_score": max_score,
        "max_attempts": max_attempts,
        "allow_revision_after_feedback": bool(
            data.get(
                "allow_revision_after_feedback",
                current.allow_revision_after_feedback,
            )
        ),
    }
    comparable = {
        key: getattr(current, key)
        for key in values
    }
    if comparable == values:
        if db.session.is_modified(assignment):
            db.session.commit()
        return jsonify(_assignment_dict(assignment, include_evaluation=True))
    version = _new_assignment_version(assignment, user_id, **values)
    if assignment.status != "published":
        _apply_assignment_version(assignment, version)
    db.session.commit()
    return jsonify(_assignment_dict(assignment, include_evaluation=True))


@education_content_api.get("/assignments/<assignment_id>/versions")
@jwt_required()
def list_assignment_versions(assignment_id):
    assignment = _assignment_for_member(assignment_id, get_jwt_identity(), "teacher")
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    _ensure_assignment_version(assignment, get_jwt_identity())
    db.session.commit()
    rows = (
        AssignmentContentVersion.query.filter_by(assignment_id=assignment.id)
        .order_by(AssignmentContentVersion.version_number.desc())
        .all()
    )
    return jsonify({"items": [_assignment_version_dict(row) for row in rows]})


@education_content_api.post("/assignments/<assignment_id>/publish")
@jwt_required()
def publish_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "teacher")
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    current = _ensure_assignment_version(assignment, user_id)
    if assignment.published_version_id != current.id:
        now = datetime.utcnow()
        assignment.status = "published"
        assignment.published_by = user_id
        assignment.published_at = now
        assignment.published_version_id = current.id
        current.published_at = now
        _apply_assignment_version(assignment, current)
        _event(
            assignment.course_id,
            user_id,
            "AssignmentPublished",
            "assignment",
            assignment.id,
        )
        for asset in _assets_for_ids(
            current.source_asset_ids,
            assignment.course_id,
        ):
            asset.visibility_scope = "course_published"
        db.session.commit()
    return jsonify(_assignment_dict(assignment, include_evaluation=True))


@education_content_api.get("/courses/<course_id>/assignments")
@jwt_required()
def list_assignments(course_id):
    user_id = get_jwt_identity()
    membership = _course_member(course_id, user_id)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = Assignment.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    assignments = query.order_by(Assignment.created_at.asc()).all()
    for assignment in assignments:
        _ensure_assignment_version(assignment, user_id)
    db.session.commit()
    return jsonify(
        {
            "items": [
                _assignment_dict(
                    row,
                    include_evaluation=membership.role == "teacher",
                    version=(
                        _assignment_version(row, row.current_version_id)
                        if membership.role == "teacher"
                        else _assignment_version(row, row.published_version_id)
                    ),
                )
                for row in assignments
            ]
        }
    )


def _course_student_names(course_id):
    memberships = CourseMembership.query.filter_by(
        course_id=course_id,
        role="student",
        status="active",
    ).order_by(CourseMembership.created_at.asc()).all()
    profiles = {
        row.user_id: row.display_name
        for row in CourseMemberProfile.query.filter_by(course_id=course_id).all()
    }
    account_profiles = {}
    try:
        account_profiles = current_app.extensions[
            "education_runtime_client"
        ].get_user_profiles(
            authorization=request.headers.get("Authorization", ""),
            user_ids=[membership.user_id for membership in memberships],
        )
    except Exception:
        account_profiles = {}
    return [
        {
            "user_id": membership.user_id,
            "display_name": (
                profiles.get(membership.user_id)
                or (account_profiles.get(membership.user_id) or {}).get("username")
                or f"学生 {index + 1:02d}"
            ),
        }
        for index, membership in enumerate(memberships)
    ]


def _current_submission_version(submission):
    if not submission or not submission.current_version_id:
        return None
    return SubmissionVersion.query.filter_by(
        id=submission.current_version_id,
        submission_id=submission.id,
    ).first()


def _answer_text(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(
            text for text in (_answer_text(item) for item in value) if text
        )
    if not isinstance(value, dict):
        return "" if value is None else str(value)
    preferred = ("writing", "text", "response", "answer", "content")
    texts = [
        _answer_text(value[key])
        for key in preferred
        if key in value and _answer_text(value[key])
    ]
    if texts:
        return "\n".join(texts)
    return "\n".join(
        text
        for key, item in value.items()
        if key not in {"id", "question_id"}
        for text in [_answer_text(item)]
        if text
    )


@education_content_api.get("/assignments/<assignment_id>/overview")
@jwt_required()
def get_assignment_overview(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "teacher")
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    students = _course_student_names(assignment.course_id)
    submissions = {
        row.student_user_id: row
        for row in Submission.query.filter_by(assignment_id=assignment.id).all()
        if row.status != "draft"
    }
    rows = []
    scores = []
    for student in students:
        submission = submissions.get(student["user_id"])
        version = _current_submission_version(submission)
        score = submission.final_score if submission else None
        if score is not None:
            scores.append(float(score))
        rows.append(
            {
                "display_name": student["display_name"],
                "submission_id": submission.id if submission else None,
                "status": submission.status if submission else "unsubmitted",
                "submitted_at": (
                    submission.submitted_at.isoformat()
                    if submission and submission.submitted_at
                    else None
                ),
                "version_number": version.version_number if version else None,
                "score": score,
                "word_count": (
                    len(_answer_text(version.answer_json)) if version else 0
                ),
                "artifact_count": len(version.artifact_ids or []) if version else 0,
            }
        )
    graded_states = {"graded"}
    revision_states = {"revision_requested"}
    submitted_count = len([row for row in rows if row["submission_id"]])
    pending_count = len(
        [
            row
            for row in rows
            if row["submission_id"]
            and row["status"] not in graded_states | revision_states
        ]
    )
    metrics = {
        "expected": len(students),
        "submitted": submitted_count,
        "unsubmitted": len(students) - submitted_count,
        "late": 0,
        "pending_review": pending_count,
        "graded": len([row for row in rows if row["status"] in graded_states]),
        "revision_requested": len(
            [row for row in rows if row["status"] in revision_states]
        ),
        "highest_score": max(scores) if scores else None,
        "lowest_score": min(scores) if scores else None,
        "average_score": (
            round(sum(scores) / len(scores), 2) if scores else None
        ),
    }
    return jsonify(
        {
            "assignment": _assignment_dict(assignment, include_evaluation=True),
            "metrics": metrics,
            "students": rows,
        }
    )


def _submission_payload(submission, include_draft=False):
    if not submission:
        return {"submission": None, "draft": None, "versions": []}
    versions = SubmissionVersion.query.filter_by(
        submission_id=submission.id
    ).order_by(SubmissionVersion.version_number.asc()).all()
    draft = None
    if include_draft and submission.draft_answer_json is not None:
        draft = {
            "answer_json": submission.draft_answer_json,
            "artifact_ids": submission.draft_artifact_ids or [],
            "updated_at": (
                submission.draft_updated_at.isoformat()
                if submission.draft_updated_at
                else None
            ),
        }
    return {
        "submission": _submission_dict(submission),
        "draft": draft,
        "versions": [_submission_version_dict(row) for row in versions],
    }


def _submission_list_item(submission):
    payload = _submission_dict(submission)
    versions = SubmissionVersion.query.filter_by(
        submission_id=submission.id
    ).order_by(SubmissionVersion.version_number.asc()).all()
    payload["versions"] = [_submission_version_dict(row) for row in versions]
    return payload


@education_content_api.put("/assignments/<assignment_id>/submission/draft")
@jwt_required()
def save_submission_draft(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "student")
    if not assignment or assignment.status != "published":
        return jsonify({"error": "assignment not found"}), 404
    data = request.get_json(silent=True) or {}
    answer = data.get("answer_json")
    artifacts = data.get("artifact_ids") or []
    if not isinstance(answer, dict):
        return jsonify({"error": "answer_json must be an object"}), 400
    if not isinstance(artifacts, list):
        return jsonify({"error": "artifact_ids must be a list"}), 400
    submission = Submission.query.filter_by(
        assignment_id=assignment.id, student_user_id=user_id
    ).first()
    if not submission:
        submission = Submission(
            assignment_id=assignment.id,
            student_user_id=user_id,
            status="draft",
            attempt_count=0,
        )
        db.session.add(submission)
    if submission.attempt_count >= assignment.max_attempts:
        return jsonify({"error": "maximum attempts reached"}), 409
    if (
        submission.status == "graded"
        and not assignment.allow_revision_after_feedback
    ):
        return jsonify({"error": "revision after feedback is disabled"}), 409
    submission.draft_answer_json = answer
    submission.draft_artifact_ids = artifacts
    submission.draft_updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_submission_payload(submission, include_draft=True))


@education_content_api.get("/assignments/<assignment_id>/submission")
@jwt_required()
def get_current_submission(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "student")
    if not assignment or assignment.status != "published":
        return jsonify({"error": "assignment not found"}), 404
    submission = Submission.query.filter_by(
        assignment_id=assignment.id, student_user_id=user_id
    ).first()
    return jsonify(_submission_payload(submission, include_draft=True))


@education_content_api.post("/assignments/<assignment_id>/submissions")
@jwt_required()
def submit_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "student")
    if not assignment or assignment.status != "published":
        return jsonify({"error": "assignment not found"}), 404
    data = request.get_json(silent=True) or {}
    submission = Submission.query.filter_by(
        assignment_id=assignment.id, student_user_id=user_id
    ).first()
    answer = data.get("answer_json")
    artifact_ids = data.get("artifact_ids")
    using_saved_draft = answer is None and submission is not None
    if answer is None and submission:
        answer = submission.draft_answer_json
        artifact_ids = submission.draft_artifact_ids
    if not isinstance(answer, dict) or not answer:
        return jsonify({"error": "answer_json is required"}), 400
    if artifact_ids is None:
        artifact_ids = []
    if not isinstance(artifact_ids, list):
        return jsonify({"error": "artifact_ids must be a list"}), 400
    if not submission:
        submission = Submission(
            assignment_id=assignment.id, student_user_id=user_id
        )
        db.session.add(submission)
        db.session.flush()
    if submission.attempt_count >= assignment.max_attempts:
        return jsonify({"error": "maximum attempts reached"}), 409
    source_version_id = data.get("source_version_id")
    if using_saved_draft and source_version_id is None:
        source_version_id = submission.current_version_id
    if submission.current_version_id and source_version_id != submission.current_version_id:
        return jsonify({"error": "source_version_id must reference the current submission"}), 409
    now = datetime.utcnow()
    version = SubmissionVersion(
        submission_id=submission.id,
        version_number=submission.attempt_count + 1,
        answer_json=answer,
        artifact_ids=artifact_ids,
        submitted_at=now,
        source_version_id=source_version_id,
        checksum=_json_checksum(answer),
    )
    db.session.add(version)
    db.session.flush()
    submission.current_version_id = version.id
    submission.attempt_count += 1
    submission.status = "submitted" if submission.attempt_count == 1 else "revised"
    submission.submitted_at = now
    submission.draft_answer_json = None
    submission.draft_artifact_ids = None
    submission.draft_updated_at = None
    _event(
        assignment.course_id,
        user_id,
        "AssignmentSubmitted",
        "submission",
        submission.id,
        {"attempt": submission.attempt_count},
    )
    db.session.commit()
    return jsonify(
        {
            "submission": _submission_dict(submission),
            "version": _submission_version_dict(version),
        }
    ), 201


@education_content_api.get("/assignments/<assignment_id>/submissions")
@jwt_required()
def list_submissions(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id)
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    membership = _membership(assignment.course_id, user_id)
    query = Submission.query.filter_by(assignment_id=assignment.id)
    if membership.role == "teacher":
        query = query.filter(Submission.status != "draft")
    else:
        query = query.filter_by(student_user_id=user_id)
    return jsonify(
        {
            "items": [
                _submission_list_item(row)
                for row in query.order_by(Submission.created_at.asc()).all()
            ]
        }
    )


def _submission_for_reviewer(submission_id, user_id):
    submission = Submission.query.filter_by(id=submission_id).first()
    if not submission:
        return None, None
    assignment = Assignment.query.filter_by(id=submission.assignment_id).first()
    if not assignment or not _membership(assignment.course_id, user_id, "teacher"):
        return None, None
    return submission, assignment


def _rubric_items(assignment):
    rubric = (assignment.evaluation_json or {}).get("rubric")
    items = []
    if isinstance(rubric, dict):
        for key, value in rubric.items():
            try:
                maximum = float(value)
            except (TypeError, ValueError):
                continue
            items.append(
                {
                    "id": str(key),
                    "label": str(key).replace("_", " ").strip().title(),
                    "max_score": maximum,
                }
            )
    elif isinstance(rubric, list):
        for index, item in enumerate(rubric):
            if not isinstance(item, dict):
                continue
            try:
                maximum = float(item.get("max_score") or item.get("score"))
            except (TypeError, ValueError):
                continue
            items.append(
                {
                    "id": str(item.get("id") or f"criterion_{index + 1}"),
                    "label": str(
                        item.get("label") or item.get("name") or f"维度 {index + 1}"
                    ),
                    "max_score": maximum,
                }
            )
    if not items:
        items = [
            {
                "id": "overall",
                "label": "整体表现",
                "max_score": float(assignment.max_score),
            }
        ]
    return items


def _review_draft_dict(draft):
    if not draft:
        return None
    return {
        "id": draft.id,
        "submission_id": draft.submission_id,
        "submission_version_id": draft.submission_version_id,
        "rubric_scores": draft.rubric_scores or {},
        "feedback_json": draft.feedback_json or {},
        "annotations": draft.annotations or [],
        "score": draft.score,
        "revision_requested": bool(draft.revision_requested),
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
    }


def _feedback_dict(feedback):
    return {
        "id": feedback.id,
        "submission_version_id": feedback.submission_version_id,
        "feedback_json": feedback.feedback_json,
        "rubric_scores": feedback.rubric_scores or {},
        "annotations": feedback.annotations or [],
        "score": feedback.score,
        "status": feedback.status,
        "version_number": feedback.version_number,
        "revision_requested": bool(feedback.revision_requested),
        "released_at": (
            feedback.released_at.isoformat() if feedback.released_at else None
        ),
    }


def _review_analysis_dict(analysis):
    if not analysis:
        return None
    return {
        "id": analysis.id,
        "submission_version_id": analysis.submission_version_id,
        "evaluation_checksum": analysis.evaluation_checksum,
        "prompt_version": analysis.prompt_version,
        "agent_run_id": analysis.agent_run_id,
        "analysis_json": analysis.analysis_json or {},
        "status": analysis.status,
        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
    }


def _submission_evidence(version, course_id):
    answer = version.answer_json if version else {}
    artifacts = _assets_for_ids(version.artifact_ids, course_id) if version else []
    items = answer.get("items") if isinstance(answer, dict) else None
    if isinstance(items, list) and items:
        rendered = []
        for index, item in enumerate(items):
            if isinstance(item, dict):
                rendered.append(
                    {
                        "index": index + 1,
                        "prompt": str(item.get("prompt") or item.get("question") or ""),
                        "answer": _answer_text(item.get("answer") or item.get("response")),
                    }
                )
        return {
            "kind": "items",
            "items": rendered,
            "text": "",
            "artifacts": [asset_to_dict(asset) for asset in artifacts],
        }
    text = _answer_text(answer)
    return {
        "kind": "text" if text else ("attachments" if artifacts else "empty"),
        "text": text,
        "items": [],
        "artifacts": [asset_to_dict(asset) for asset in artifacts],
    }


def _review_navigation(assignment_id, submission_id):
    rows = (
        Submission.query.filter(
            Submission.assignment_id == assignment_id,
            Submission.status != "draft",
        )
        .order_by(Submission.created_at.asc())
        .all()
    )
    ids = [row.id for row in rows]
    try:
        index = ids.index(submission_id)
    except ValueError:
        return {"previous_submission_id": None, "next_submission_id": None}
    return {
        "previous_submission_id": ids[index - 1] if index > 0 else None,
        "next_submission_id": ids[index + 1] if index + 1 < len(ids) else None,
    }


@education_content_api.get("/submissions/<submission_id>/review")
@jwt_required()
def get_submission_review(submission_id):
    user_id = get_jwt_identity()
    submission, assignment = _submission_for_reviewer(submission_id, user_id)
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    version = _current_submission_version(submission)
    if not version:
        return jsonify({"error": "submission version not found"}), 404
    student_name = next(
        (
            row["display_name"]
            for row in _course_student_names(assignment.course_id)
            if row["user_id"] == submission.student_user_id
        ),
        "未命名学生",
    )
    draft = ReviewDraft.query.filter_by(
        submission_version_id=version.id,
        saved_by=user_id,
    ).first()
    evaluation_checksum = _json_checksum(assignment.evaluation_json or {})
    analysis = SubmissionReviewAnalysis.query.filter_by(
        submission_version_id=version.id,
        evaluation_checksum=evaluation_checksum,
        prompt_version=SUBMISSION_REVIEW_PROMPT_VERSION,
        status="ready",
    ).first()
    stale_exists = SubmissionReviewAnalysis.query.filter_by(
        submission_id=submission.id,
        status="ready",
    ).first()
    feedbacks = Feedback.query.filter_by(
        submission_version_id=version.id
    ).order_by(Feedback.version_number.asc()).all()
    return jsonify(
        {
            "assignment": _assignment_dict(assignment, include_evaluation=True),
            "student": {
                "display_name": student_name,
            },
            "submission": _submission_dict(submission),
            "version": _submission_version_dict(version),
            "evidence": _submission_evidence(version, assignment.course_id),
            "rubric": _rubric_items(assignment),
            "review_draft": _review_draft_dict(draft),
            "feedback_versions": [_feedback_dict(row) for row in feedbacks],
            "analysis_state": (
                "ready" if analysis else ("stale" if stale_exists else "missing")
            ),
            "analysis": _review_analysis_dict(analysis or stale_exists),
            "analysis_cache_key": {
                "submission_version_id": version.id,
                "evaluation_checksum": evaluation_checksum,
                "prompt_version": SUBMISSION_REVIEW_PROMPT_VERSION,
            },
            "navigation": _review_navigation(assignment.id, submission.id),
        }
    )


def _validated_review_draft(data, assignment):
    scores = data.get("rubric_scores") or {}
    feedback_json = data.get("feedback_json") or {}
    annotations = data.get("annotations") or []
    if not isinstance(scores, dict):
        raise ValueError("rubric_scores must be an object")
    if not isinstance(feedback_json, dict):
        raise ValueError("feedback_json must be an object")
    if not isinstance(annotations, list) or len(annotations) > 200:
        raise ValueError("annotations must be a list of at most 200 items")
    criteria = {item["id"]: item for item in _rubric_items(assignment)}
    normalized_scores = {}
    for key, value in scores.items():
        if key not in criteria:
            raise ValueError(f"unknown rubric criterion: {key}")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"rubric score for {key} must be numeric") from error
        if not 0 <= number <= criteria[key]["max_score"]:
            raise ValueError(f"rubric score for {key} is out of range")
        normalized_scores[key] = number
    score = sum(normalized_scores.values()) if normalized_scores else None
    return {
        "rubric_scores": normalized_scores,
        "feedback_json": feedback_json,
        "annotations": annotations,
        "score": score,
        "revision_requested": bool(data.get("revision_requested", False)),
    }


@education_content_api.put("/submissions/<submission_id>/review-draft")
@jwt_required()
def save_review_draft(submission_id):
    user_id = get_jwt_identity()
    submission, assignment = _submission_for_reviewer(submission_id, user_id)
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    version = _current_submission_version(submission)
    if not version:
        return jsonify({"error": "submission version not found"}), 404
    try:
        values = _validated_review_draft(request.get_json(silent=True) or {}, assignment)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    draft = ReviewDraft.query.filter_by(
        submission_version_id=version.id,
        saved_by=user_id,
    ).first()
    if not draft:
        draft = ReviewDraft(
            submission_id=submission.id,
            submission_version_id=version.id,
            saved_by=user_id,
        )
        db.session.add(draft)
    for key, value in values.items():
        setattr(draft, key, value)
    if submission.status in {"submitted", "revised"}:
        submission.status = "reviewing"
    db.session.commit()
    return jsonify(_review_draft_dict(draft))


@education_content_api.post("/submissions/<submission_id>/review/publish")
@jwt_required()
def publish_submission_review(submission_id):
    user_id = get_jwt_identity()
    submission, assignment = _submission_for_reviewer(submission_id, user_id)
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    version = _current_submission_version(submission)
    draft = (
        ReviewDraft.query.filter_by(
            submission_version_id=version.id,
            saved_by=user_id,
        ).first()
        if version
        else None
    )
    if not draft:
        return jsonify({"error": "review draft is required"}), 409
    prior_count = Feedback.query.filter_by(
        submission_version_id=version.id
    ).count()
    feedback = Feedback(
        submission_version_id=version.id,
        feedback_json=draft.feedback_json or {},
        status="released",
        version_number=prior_count + 1,
        rubric_scores=draft.rubric_scores or {},
        annotations=draft.annotations or [],
        revision_requested=bool(draft.revision_requested),
        score=draft.score,
        released_by=user_id,
    )
    db.session.add(feedback)
    submission.status = (
        "revision_requested" if draft.revision_requested else "graded"
    )
    submission.final_score = draft.score
    submission.graded_by = user_id
    submission.graded_at = datetime.utcnow()
    _event(
        assignment.course_id,
        user_id,
        "FeedbackReleased",
        "submission",
        submission.id,
        {
            "student_user_id": submission.student_user_id,
            "score": draft.score,
            "revision_requested": bool(draft.revision_requested),
        },
    )
    from .learning_service import ensure_weakness_snapshot

    ensure_weakness_snapshot(assignment.course_id, submission.student_user_id)
    db.session.delete(draft)
    db.session.commit()
    return jsonify(_feedback_dict(feedback)), 201


@education_content_api.post("/submissions/<submission_id>/feedback")
@jwt_required()
def release_feedback(submission_id):
    user_id = get_jwt_identity()
    submission, assignment = _submission_for_reviewer(submission_id, user_id)
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    data = request.get_json(silent=True) or {}
    feedback_json = data.get("feedback_json")
    if not isinstance(feedback_json, dict) or not feedback_json:
        return jsonify({"error": "feedback_json is required"}), 400
    try:
        score = float(data["score"]) if data.get("score") is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "score must be numeric"}), 400
    if score is not None and not 0 <= score <= assignment.max_score:
        return jsonify({"error": "score must be within assignment max_score"}), 400
    prior_count = Feedback.query.filter_by(
        submission_version_id=submission.current_version_id
    ).count()
    feedback = Feedback(
        submission_version_id=submission.current_version_id,
        feedback_json=feedback_json,
        status="released",
        version_number=prior_count + 1,
        rubric_scores=(
            data.get("rubric_scores")
            if isinstance(data.get("rubric_scores"), dict)
            else {}
        ),
        annotations=(
            data.get("annotations")
            if isinstance(data.get("annotations"), list)
            else []
        ),
        revision_requested=bool(data.get("revision_requested", False)),
        score=score,
        released_by=user_id,
    )
    db.session.add(feedback)
    submission.status = (
        "revision_requested" if feedback.revision_requested else "graded"
    )
    submission.final_score = score
    submission.graded_by = user_id
    submission.graded_at = datetime.utcnow()
    _event(
        assignment.course_id,
        user_id,
        "FeedbackReleased",
        "submission",
        submission.id,
        {"student_user_id": submission.student_user_id, "score": score},
    )
    from .learning_service import ensure_weakness_snapshot

    ensure_weakness_snapshot(assignment.course_id, submission.student_user_id)
    db.session.commit()
    return jsonify(_feedback_dict(feedback)), 201


@education_content_api.get("/submissions/<submission_id>/feedback")
@jwt_required()
def list_feedback(submission_id):
    user_id = get_jwt_identity()
    submission = Submission.query.filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    assignment = Assignment.query.filter_by(id=submission.assignment_id).first()
    membership = _membership(assignment.course_id, user_id)
    if not membership or (
        membership.role != "teacher" and submission.student_user_id != user_id
    ):
        return jsonify({"error": "submission not found"}), 404
    versions = SubmissionVersion.query.filter_by(submission_id=submission.id).all()
    version_ids = [row.id for row in versions]
    rows = (
        Feedback.query.filter(Feedback.submission_version_id.in_(version_ids))
        .order_by(Feedback.released_at.asc())
        .all()
        if version_ids
        else []
    )
    return jsonify(
        {
            "items": [_feedback_dict(row) for row in rows]
        }
    )


@education_content_api.post("/resources/search")
@jwt_required()
def search_resources():
    """Run a membership-scoped research pipeline or return safe fallback."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    query = str(data.get("query") or "").strip()
    course_id = str(data.get("course_id") or "").strip()
    if not query or not course_id:
        return jsonify({"error": "query and course_id are required"}), 400
    if not _membership(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    try:
        limit = max(1, min(int(data.get("limit") or 5), 20))
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    pipeline = current_app.config.get("EDUCATION_RESOURCE_PIPELINE")
    if pipeline is None:
        return jsonify(
            {
                "query": query,
                "provider_index": None,
                "results": [],
                "diagnostics": [
                    {
                        "stage": "search",
                        "status": "unconfigured",
                        "message": (
                            "No external SearchProvider is configured; "
                            "continue with course-scoped RAG materials."
                        ),
                    }
                ],
                "fallback_exhausted": True,
            }
        )

    from .resource_pipeline import ResourceScope

    scope = ResourceScope(
        user_id=user_id,
        domain="edu",
        course_ids=(course_id,),
    )
    try:
        result = pipeline.research(query, scope=scope, limit=limit)
    except Exception as exc:
        return jsonify(
            {
                "query": query,
                "provider_index": None,
                "results": [],
                "diagnostics": [
                    {
                        "stage": "pipeline",
                        "status": "error",
                        "error": str(exc),
                    }
                ],
                "fallback_exhausted": True,
            }
        )
    return jsonify(result)


@education_content_api.get("/courses/<course_id>/analytics")
@jwt_required()
def course_analytics(course_id):
    user_id = get_jwt_identity()
    if not _teacher_course(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    active_students = CourseMembership.query.filter_by(
        course_id=course_id, role="student", status="active"
    ).count()
    assignments = Assignment.query.filter_by(
        course_id=course_id, status="published"
    ).all()
    lessons_by_id = {
        row.id: row
        for row in Lesson.query.filter_by(course_id=course_id).all()
    }
    learning_domain_counts = {}
    assignment_kind_counts = {}
    for assignment in assignments:
        assignment_kind_counts[assignment.kind] = (
            assignment_kind_counts.get(assignment.kind, 0) + 1
        )
        lesson = lessons_by_id.get(assignment.lesson_id)
        if lesson:
            learning_domain_counts[lesson.learning_domain] = (
                learning_domain_counts.get(lesson.learning_domain, 0) + 1
            )
    assignment_ids = [row.id for row in assignments]
    submissions = (
        Submission.query.filter(Submission.assignment_id.in_(assignment_ids)).all()
        if assignment_ids
        else []
    )
    submitted_students = len({row.student_user_id for row in submissions})
    denominator = active_students * len(assignments)
    completion_rate = round(len(submissions) / denominator, 4) if denominator else 0.0
    scores = [row.final_score for row in submissions if row.final_score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else None
    event_rows = (
        db.session.query(LearningEvent.event_type, db.func.count(LearningEvent.id))
        .filter(LearningEvent.course_id == course_id)
        .group_by(LearningEvent.event_type)
        .all()
    )
    return jsonify(
        {
            "course_id": course_id,
            "active_students": active_students,
            "published_assignments": len(assignments),
            "submitted_students": submitted_students,
            "completion_rate": completion_rate,
            "average_score": average_score,
            "learning_domain_counts": learning_domain_counts,
            "assignment_kind_counts": assignment_kind_counts,
            "event_counts": {event_type: count for event_type, count in event_rows},
        }
    )
