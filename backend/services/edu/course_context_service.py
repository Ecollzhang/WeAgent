"""Stable course/lesson projections shared by product UI and Agent tools."""

import hashlib
import json

from .asset_models import EducationAsset
from .content_models import (
    EducationContent,
    EducationContentVersion,
    EducationMaterial,
    Lesson,
    LessonActivity,
)
from .extensions import db
from .knowledge_models import KnowledgeResource
from .knowledge_service import knowledge_resource_to_dict
from .models import Course


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
        "current_published_version_id": lesson.current_published_version_id,
    }


def _content_projection(content):
    version = (
        db.session.get(EducationContentVersion, content.current_version_id)
        if content.current_version_id
        else None
    )
    if not version:
        return None
    return {
        "content_id": content.id,
        "kind": content.kind,
        "status": content.status,
        "visibility_scope": content.visibility_scope,
        "version_id": version.id,
        "version_number": version.version_number,
        "schema_name": version.schema_name,
        "schema_version": version.schema_version,
        "source_json": version.source_json or {},
        "rendered_html": version.rendered_html,
        "change_summary": version.change_summary,
        "source_agent_run_id": version.source_agent_run_id,
        "checksum": version.checksum,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def _activity_projection(activity):
    return {
        "id": activity.id,
        "activity_type": activity.activity_type,
        "title": activity.title,
        "position": activity.position,
        "content_version_id": activity.content_version_id,
        "student_payload": activity.student_payload or {},
        "teacher_payload": activity.teacher_payload or {},
        "status": activity.status,
    }


def _material_projection(material):
    return {
        "id": material.id,
        "asset_id": material.asset_id,
        "title": material.title,
        "original_filename": material.original_filename,
        "extension": material.extension,
        "mime_type": material.mime_type,
        "file_size": material.file_size,
        "status": material.status,
    }


def _asset_material_projection(asset):
    filename = str(asset.original_filename or "")
    return {
        "id": asset.id,
        "asset_id": asset.id,
        "title": asset.title,
        "original_filename": filename,
        "extension": filename.rsplit(".", 1)[-1].lower() if "." in filename else "",
        "mime_type": asset.media_type,
        "file_size": asset.byte_size,
        "status": asset.status,
        "visibility_scope": asset.visibility_scope,
    }


def build_courseware_context(course_id, lesson_id):
    """Return the reproducible, teacher-private context for one lesson."""
    course = Course.query.filter_by(id=course_id, status="active").first()
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first()
    if not course or not lesson:
        return None

    contents = (
        EducationContent.query.filter_by(
            course_id=course_id,
            lesson_id=lesson_id,
        )
        .filter(EducationContent.status != "archived")
        .order_by(EducationContent.updated_at.desc())
        .all()
    )
    projected = [row for row in (_content_projection(item) for item in contents) if row]
    lesson_plan = next(
        (item for item in projected if item["kind"] == "lesson_plan"),
        None,
    )
    slide_documents = [
        item for item in projected if item["kind"] == "slide_document"
    ]
    activities = (
        LessonActivity.query.filter_by(course_id=course_id, lesson_id=lesson_id)
        .filter(LessonActivity.status != "archived")
        .order_by(LessonActivity.position.asc(), LessonActivity.created_at.asc())
        .all()
    )
    canonical_assets = (
        EducationAsset.query.filter_by(
            course_id=course_id,
            lesson_id=lesson_id,
            status="active",
        )
        .filter(EducationAsset.purpose.in_(("courseware", "lesson_material")))
        .order_by(EducationAsset.created_at.desc())
        .all()
    )
    canonical_asset_ids = {item.id for item in canonical_assets}
    legacy_materials = (
        EducationMaterial.query.filter_by(course_id=course_id, lesson_id=lesson_id)
        .filter(EducationMaterial.status != "archived")
        .order_by(EducationMaterial.created_at.desc())
        .all()
    )
    legacy_materials = [
        item
        for item in legacy_materials
        if not item.asset_id or item.asset_id not in canonical_asset_ids
    ]
    materials = [
        *[_asset_material_projection(item) for item in canonical_assets],
        *[_material_projection(item) for item in legacy_materials],
    ]
    resources = (
        KnowledgeResource.query.filter_by(course_id=course_id, status="active")
        .order_by(KnowledgeResource.updated_at.desc())
        .all()
    )
    checksum_basis = {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "lesson_plan_version_id": lesson_plan["version_id"] if lesson_plan else None,
        "slide_version_ids": [item["version_id"] for item in slide_documents],
        "activity_ids": [item.id for item in activities],
        "material_ids": [item["asset_id"] or item["id"] for item in materials],
        "knowledge_resource_ids": [item.id for item in resources],
    }
    checksum = hashlib.sha256(
        json.dumps(checksum_basis, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "course": course.to_dict("teacher"),
        "lesson": _lesson_dict(lesson),
        "lesson_plan": lesson_plan,
        "slide_documents": slide_documents,
        "activities": [_activity_projection(item) for item in activities],
        "materials": materials,
        "knowledge_resources": [
            knowledge_resource_to_dict(item) for item in resources
        ],
        "context_checksum": checksum,
    }
