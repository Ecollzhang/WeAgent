"""Course and membership HTTP API."""

import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .extensions import db
from .models import Course, CourseInvitation, CourseMembership


education_api = Blueprint("education_api", __name__)
SUPPORTED_COURSES = {
    ("high_school_english", "senior_high"),
    ("primary_chinese", "primary"),
}


def token_hash(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def active_membership(course_id, user_id, role=None):
    query = CourseMembership.query.filter_by(
        course_id=course_id,
        user_id=user_id,
        status="active",
    )
    if role:
        query = query.filter_by(role=role)
    return query.first()


def teacher_course_or_none(course_id, user_id):
    membership = active_membership(course_id, user_id, role="teacher")
    if not membership:
        return None
    return Course.query.filter_by(id=course_id).first()


@education_api.post("/courses")
@jwt_required()
def create_course():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    subject_code = str(data.get("subject_code") or "").strip()
    grade_band = str(data.get("grade_band") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    if (subject_code, grade_band) not in SUPPORTED_COURSES:
        return jsonify({"error": "unsupported subject_code and grade_band"}), 400

    now = datetime.utcnow()
    course = Course(
        title=title,
        subject_code=subject_code,
        grade_band=grade_band,
        description=str(data.get("description") or "").strip(),
        owner_user_id=user_id,
        status="active",
    )
    membership = CourseMembership(
        course=course,
        user_id=user_id,
        role="teacher",
        status="active",
        joined_at=now,
    )
    db.session.add_all([course, membership])
    db.session.commit()
    return jsonify(course.to_dict(membership_role="teacher")), 201


@education_api.get("/courses")
@jwt_required()
def list_courses():
    user_id = get_jwt_identity()
    rows = (
        db.session.query(Course, CourseMembership)
        .join(CourseMembership, CourseMembership.course_id == Course.id)
        .filter(
            CourseMembership.user_id == user_id,
            CourseMembership.status == "active",
            Course.status != "archived",
        )
        .order_by(Course.created_at.asc())
        .all()
    )
    return jsonify(
        {"items": [course.to_dict(member.role) for course, member in rows]}
    )


@education_api.get("/courses/<course_id>/members")
@jwt_required()
def list_members(course_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    members = CourseMembership.query.filter_by(
        course_id=course_id,
        status="active",
    ).order_by(CourseMembership.created_at.asc()).all()
    return jsonify({"items": [member.to_dict() for member in members]})


@education_api.post("/courses/<course_id>/invitations")
@jwt_required()
def create_invitation(course_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        max_uses = int(data.get("max_uses", 30))
        expires_in_hours = int(data.get("expires_in_hours", 168))
    except (TypeError, ValueError):
        return jsonify({"error": "invitation limits must be integers"}), 400
    if not 1 <= max_uses <= 1000 or not 1 <= expires_in_hours <= 24 * 90:
        return jsonify({"error": "invalid invitation limits"}), 400

    raw_token = secrets.token_urlsafe(24)
    invitation = CourseInvitation(
        course_id=course_id,
        token_hash=token_hash(raw_token),
        created_by=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        max_uses=max_uses,
        status="active",
    )
    db.session.add(invitation)
    db.session.commit()
    response = invitation.to_dict()
    response["token"] = raw_token
    return jsonify(response), 201


@education_api.delete("/courses/<course_id>/invitations/<invitation_id>")
@jwt_required()
def revoke_invitation(course_id, invitation_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    invitation = CourseInvitation.query.filter_by(
        id=invitation_id,
        course_id=course_id,
    ).first()
    if not invitation:
        return jsonify({"error": "invitation not found"}), 404
    invitation.status = "revoked"
    db.session.commit()
    return jsonify(invitation.to_dict())


@education_api.post("/invitations/accept")
@jwt_required()
def accept_invitation():
    user_id = get_jwt_identity()
    raw_token = str((request.get_json(silent=True) or {}).get("token") or "").strip()
    if not raw_token:
        return jsonify({"error": "token is required"}), 400

    invitation = CourseInvitation.query.filter_by(
        token_hash=token_hash(raw_token)
    ).first()
    if not invitation:
        return jsonify({"error": "invitation is invalid"}), 404

    existing = CourseMembership.query.filter_by(
        course_id=invitation.course_id,
        user_id=user_id,
    ).first()
    if existing and existing.status == "active":
        return jsonify({"membership": existing.to_dict(), "joined": False})

    now = datetime.utcnow()
    if (
        invitation.status != "active"
        or invitation.expires_at <= now
        or invitation.used_count >= invitation.max_uses
    ):
        return jsonify({"error": "invitation is no longer available"}), 410

    if existing:
        existing.role = "student"
        existing.status = "active"
        existing.invited_by = invitation.created_by
        existing.joined_at = now
        existing.removed_at = None
        membership = existing
    else:
        membership = CourseMembership(
            course_id=invitation.course_id,
            user_id=user_id,
            role="student",
            status="active",
            invited_by=invitation.created_by,
            joined_at=now,
        )
        db.session.add(membership)

    invitation.used_count += 1
    if invitation.used_count >= invitation.max_uses:
        invitation.status = "expired"
    db.session.commit()
    return jsonify({"membership": membership.to_dict(), "joined": True})
