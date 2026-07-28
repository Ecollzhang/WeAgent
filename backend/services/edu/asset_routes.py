"""HTTP boundary for durable Education assets."""

from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from .access import active_membership
from .asset_models import EducationAsset
from .asset_service import (
    ASSET_VISIBILITY,
    AssetServiceError,
    adopt_legacy_material,
    asset_to_dict,
    create_database_asset,
    validate_asset_access,
)
from .content_models import EducationMaterial
from .extensions import db


education_asset_api = Blueprint("education_asset_api", __name__)


def _asset_error(error):
    return jsonify({"error": error.message, "error_code": error.error_code}), error.status_code


@education_asset_api.post("/courses/<course_id>/assets")
@jwt_required()
def upload_asset(course_id):
    actor = get_jwt_identity()
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "file is required", "error_code": "file_required"}), 400
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
    try:
        asset = create_database_asset(
            course_id=course_id,
            lesson_id=request.form.get("lesson_id") or None,
            actor_user_id=actor,
            content=content,
            original_filename=uploaded.filename,
            media_type=uploaded.mimetype or "application/octet-stream",
            title=request.form.get("title") or uploaded.filename,
            purpose=request.form.get("purpose") or "course_material",
            visibility_scope=request.form.get("visibility_scope") or "course_teacher",
        )
        db.session.commit()
    except AssetServiceError as error:
        db.session.rollback()
        return _asset_error(error)
    return jsonify(asset_to_dict(asset)), 201


@education_asset_api.get("/courses/<course_id>/assets")
@jwt_required()
def list_assets(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = EducationAsset.query.filter_by(course_id=course_id, status="active")
    if membership.role != "teacher":
        query = query.filter(
            db.or_(
                EducationAsset.visibility_scope == "course_published",
                db.and_(
                    EducationAsset.visibility_scope == "owner_private",
                    EducationAsset.owner_user_id == actor,
                ),
            )
        )
    rows = query.order_by(EducationAsset.created_at.desc()).all()
    return jsonify({"items": [asset_to_dict(row) for row in rows]})


@education_asset_api.get("/assets/<asset_id>")
@jwt_required()
def get_asset(asset_id):
    asset = EducationAsset.query.filter_by(id=asset_id).first()
    if not asset:
        return jsonify({"error": "asset not found"}), 404
    try:
        validate_asset_access(asset, get_jwt_identity())
    except AssetServiceError as error:
        return _asset_error(error)
    return jsonify(asset_to_dict(asset))


@education_asset_api.patch("/assets/<asset_id>")
@jwt_required()
def update_asset(asset_id):
    asset = EducationAsset.query.filter_by(id=asset_id).first()
    if not asset:
        return jsonify({"error": "asset not found"}), 404
    try:
        validate_asset_access(asset, get_jwt_identity(), write=True)
    except AssetServiceError as error:
        return _asset_error(error)
    data = request.get_json(silent=True) or {}
    if "visibility_scope" in data:
        visibility = str(data["visibility_scope"])
        if visibility not in ASSET_VISIBILITY:
            return jsonify(
                {
                    "error": "unsupported visibility_scope",
                    "error_code": "invalid_visibility",
                }
            ), 400
        asset.visibility_scope = visibility
    if "title" in data:
        title = str(data["title"] or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        asset.title = title
    db.session.commit()
    return jsonify(asset_to_dict(asset))


@education_asset_api.get("/assets/<asset_id>/download")
@jwt_required()
def download_asset(asset_id):
    asset = EducationAsset.query.filter_by(id=asset_id).first()
    if not asset:
        return jsonify({"error": "asset not found"}), 404
    try:
        validate_asset_access(asset, get_jwt_identity())
    except AssetServiceError as error:
        return _asset_error(error)
    return send_file(
        BytesIO(asset.blob_bytes),
        mimetype=asset.media_type,
        as_attachment=True,
        download_name=asset.original_filename,
    )


@education_asset_api.post("/materials/<material_id>/adopt")
@jwt_required()
def adopt_material(material_id):
    material = EducationMaterial.query.filter_by(id=material_id).first()
    if not material:
        return jsonify({"error": "material not found"}), 404
    try:
        asset = adopt_legacy_material(
            material,
            get_jwt_identity(),
            max_bytes=int(
                current_app.config.get(
                    "EDUCATION_MAX_UPLOAD_BYTES",
                    25 * 1024 * 1024,
                )
            ),
        )
        db.session.commit()
    except AssetServiceError as error:
        db.session.rollback()
        return _asset_error(error)
    payload = asset_to_dict(asset)
    payload["asset_id"] = asset.id
    payload["material_id"] = material.id
    return jsonify(payload)
