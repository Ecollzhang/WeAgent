"""Application service for persistent Education assets."""

import hashlib
import os
from dataclasses import dataclass

from .access import active_membership, is_teacher
from .asset_models import EducationAsset
from .extensions import db


ASSET_VISIBILITY = {"owner_private", "course_teacher", "course_published"}
ASSET_PURPOSES = {
    "course_material",
    "lesson_material",
    "assignment_source",
    "knowledge_resource",
    "courseware",
    "roster",
    "agent_output",
    "student_submission",
}


@dataclass
class AssetServiceError(Exception):
    message: str
    status_code: int = 400
    error_code: str = "invalid_asset"


def asset_storage_capacity_error():
    return AssetServiceError(
        "asset storage could not persist the uploaded file",
        422,
        "asset_storage_capacity_exceeded",
    )


def asset_to_dict(asset):
    return {
        "id": asset.id,
        "course_id": asset.course_id,
        "lesson_id": asset.lesson_id,
        "owner_user_id": asset.owner_user_id,
        "purpose": asset.purpose,
        "title": asset.title,
        "original_filename": asset.original_filename,
        "media_type": asset.media_type,
        "byte_size": asset.byte_size,
        "sha256": asset.sha256,
        "visibility_scope": asset.visibility_scope,
        "storage_backend": asset.storage_backend,
        "status": asset.status,
        "source_agent_run_id": asset.source_agent_run_id,
        "download_url": f"/api/edu/assets/{asset.id}/download",
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


def validate_asset_access(asset, actor_user_id, *, write=False):
    membership = active_membership(asset.course_id, actor_user_id)
    if not membership or asset.status != "active":
        raise AssetServiceError("asset not found", 404, "asset_not_found")
    if write and membership.role != "teacher":
        raise AssetServiceError("asset not found", 404, "asset_not_found")
    if membership.role == "teacher":
        return membership
    if asset.visibility_scope == "course_published":
        return membership
    if asset.visibility_scope == "owner_private" and asset.owner_user_id == actor_user_id:
        return membership
    raise AssetServiceError("asset not found", 404, "asset_not_found")


def asset_dependencies(asset):
    """Return durable business objects that make an asset unsafe to archive."""
    from .content_models import Assignment, AssignmentImportJob, EducationMaterial
    from .knowledge_models import KnowledgeResource

    dependencies = []
    for assignment in Assignment.query.filter_by(
        course_id=asset.course_id,
        status="published",
    ).all():
        if asset.id in (assignment.source_asset_ids or []):
            dependencies.append(
                {
                    "type": "published_assignment",
                    "id": assignment.id,
                    "title": assignment.title,
                }
            )
    for resource in KnowledgeResource.query.filter_by(
        asset_id=asset.id,
        status="active",
    ).all():
        dependencies.append(
            {
                "type": "knowledge_resource",
                "id": resource.id,
                "title": resource.title,
            }
        )
    for material in EducationMaterial.query.filter_by(
        asset_id=asset.id,
        status="published",
    ).all():
        dependencies.append(
            {
                "type": "published_lesson_material",
                "id": material.id,
                "title": material.title,
            }
        )
    for job in AssignmentImportJob.query.filter_by(source_asset_id=asset.id).all():
        if job.status not in {"failed", "cancelled"}:
            dependencies.append(
                {
                    "type": "assignment_import",
                    "id": job.id,
                    "title": asset.title,
                }
            )
    return sorted(dependencies, key=lambda item: (item["type"], item["id"]))


def create_database_asset(
    *,
    course_id,
    actor_user_id,
    content,
    original_filename,
    media_type,
    title,
    purpose="course_material",
    visibility_scope="course_teacher",
    lesson_id=None,
    source_agent_run_id=None,
    source_sandbox_path=None,
    require_teacher=True,
):
    membership = active_membership(course_id, actor_user_id)
    if not membership or (require_teacher and membership.role != "teacher"):
        raise AssetServiceError("course not found", 404, "course_not_found")
    if not isinstance(content, bytes) or not content:
        raise AssetServiceError("file is empty", 400, "empty_asset")
    if visibility_scope not in ASSET_VISIBILITY:
        raise AssetServiceError(
            "unsupported visibility_scope", 400, "invalid_visibility"
        )
    if purpose not in ASSET_PURPOSES:
        raise AssetServiceError("unsupported purpose", 400, "invalid_purpose")
    filename = str(original_filename or "").strip()
    if not filename:
        raise AssetServiceError("original_filename is required")
    asset = EducationAsset(
        course_id=course_id,
        lesson_id=lesson_id,
        owner_user_id=actor_user_id,
        purpose=purpose,
        title=str(title or filename).strip() or filename,
        original_filename=filename,
        media_type=str(media_type or "application/octet-stream"),
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        visibility_scope=visibility_scope,
        storage_backend="database",
        blob_bytes=content,
        source_agent_run_id=source_agent_run_id,
        source_sandbox_path=source_sandbox_path,
    )
    db.session.add(asset)
    db.session.flush()
    return asset


def adopt_legacy_material(material, actor_user_id, *, max_bytes):
    if not is_teacher(material.course_id, actor_user_id):
        raise AssetServiceError("material not found", 404, "material_not_found")
    if material.asset_id:
        asset = EducationAsset.query.filter_by(id=material.asset_id).first()
        if asset:
            return asset
    path = str(material.storage_path or "")
    if not path or not os.path.isfile(path):
        raise AssetServiceError(
            "legacy material file is unavailable",
            404,
            "legacy_file_unavailable",
        )
    byte_size = os.path.getsize(path)
    if byte_size < 1 or byte_size > max_bytes:
        raise AssetServiceError(
            "material is empty or exceeds the upload limit",
            400,
            "asset_size_invalid",
        )
    with open(path, "rb") as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise AssetServiceError(
            "material exceeds the upload limit",
            400,
            "asset_size_invalid",
        )
    asset = create_database_asset(
        course_id=material.course_id,
        lesson_id=material.lesson_id,
        actor_user_id=actor_user_id,
        content=content,
        original_filename=material.original_filename,
        media_type=material.mime_type,
        title=material.title,
        purpose="lesson_material",
        visibility_scope=(
            "course_published"
            if material.status == "published"
            else "course_teacher"
        ),
    )
    material.asset_id = asset.id
    return asset
