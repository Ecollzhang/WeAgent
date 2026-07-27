"""Education domain persistence models."""

import uuid
from datetime import datetime

from .extensions import db


def new_id():
    return str(uuid.uuid4())


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Course(TimestampMixin, db.Model):
    __tablename__ = "edu_courses"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    title = db.Column(db.String(200), nullable=False)
    subject_code = db.Column(db.String(50), nullable=False)
    grade_band = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    subject_pack_version_id = db.Column(db.String(100))
    status = db.Column(db.String(20), nullable=False, default="active")

    memberships = db.relationship(
        "CourseMembership",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def to_dict(self, membership_role=None):
        result = {
            "id": self.id,
            "title": self.title,
            "subject_code": self.subject_code,
            "grade_band": self.grade_band,
            "description": self.description,
            "owner_user_id": self.owner_user_id,
            "subject_pack_version_id": self.subject_pack_version_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if membership_role:
            result["membership_role"] = membership_role
        return result


class CourseMembership(TimestampMixin, db.Model):
    __tablename__ = "edu_course_memberships"
    __table_args__ = (
        db.UniqueConstraint("course_id", "user_id", name="uq_edu_course_user"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.String(100), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    invited_by = db.Column(db.String(100))
    joined_at = db.Column(db.DateTime)
    removed_at = db.Column(db.DateTime)

    course = db.relationship("Course", back_populates="memberships")

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "invited_by": self.invited_by,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class CourseInvitation(TimestampMixin, db.Model):
    __tablename__ = "edu_course_invitations"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_by = db.Column(db.String(100), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False, default=30)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="active")

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "created_by": self.created_by,
            "expires_at": self.expires_at.isoformat(),
            "max_uses": self.max_uses,
            "used_count": self.used_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
