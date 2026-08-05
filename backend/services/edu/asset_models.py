"""Durable binary assets owned by the Education database."""

from datetime import datetime

from sqlalchemy.dialects.mysql import LONGBLOB

from .extensions import db
from .models import TimestampMixin, new_id


class EducationAsset(TimestampMixin, db.Model):
    __tablename__ = "edu_assets"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    purpose = db.Column(db.String(50), nullable=False, default="course_material")
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(120), nullable=False)
    byte_size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False, index=True)
    visibility_scope = db.Column(
        db.String(30),
        nullable=False,
        default="course_teacher",
        index=True,
    )
    storage_backend = db.Column(db.String(30), nullable=False, default="database")
    blob_bytes = db.Column(
        db.LargeBinary().with_variant(LONGBLOB(), "mysql"),
        nullable=False,
    )
    source_agent_run_id = db.Column(db.String(100), nullable=True, index=True)
    source_sandbox_path = db.Column(db.String(1000), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    archived_at = db.Column(db.DateTime, nullable=True)

    def archive(self):
        self.status = "archived"
        self.archived_at = datetime.utcnow()
