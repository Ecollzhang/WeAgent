"""Versioned lesson, assignment, submission, and learning-event models."""

from datetime import datetime

from .extensions import db
from .models import TimestampMixin, new_id


class CourseUnit(TimestampMixin, db.Model):
    __tablename__ = "edu_course_units"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="active")


class Lesson(TimestampMixin, db.Model):
    __tablename__ = "edu_lessons"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    unit_id = db.Column(
        db.String(36), db.ForeignKey("edu_course_units.id", ondelete="SET NULL"),
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    learning_domain = db.Column(db.String(20), nullable=False)
    theme_code = db.Column(db.String(100), nullable=False)
    text_genre_code = db.Column(db.String(100), nullable=False)
    lesson_type_code = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="draft")
    current_published_version_id = db.Column(db.String(36))


class LessonActivity(TimestampMixin, db.Model):
    __tablename__ = "edu_lesson_activities"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lesson_id = db.Column(
        db.String(36), db.ForeignKey("edu_lessons.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    activity_type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    content_version_id = db.Column(db.String(36))
    student_payload = db.Column(db.JSON, nullable=False, default=dict)
    teacher_payload = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(20), nullable=False, default="draft")


class EducationContent(TimestampMixin, db.Model):
    __tablename__ = "edu_contents"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lesson_id = db.Column(
        db.String(36), db.ForeignKey("edu_lessons.id", ondelete="CASCADE"),
        index=True,
    )
    kind = db.Column(db.String(40), nullable=False)
    owner_user_id = db.Column(db.String(100), nullable=False)
    visibility_scope = db.Column(
        db.String(30), nullable=False, default="course_teacher"
    )
    current_version_id = db.Column(db.String(36))
    status = db.Column(db.String(20), nullable=False, default="draft")


class EducationContentVersion(db.Model):
    __tablename__ = "edu_content_versions"
    __table_args__ = (
        db.UniqueConstraint("content_id", "version_number", name="uq_edu_content_version"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    content_id = db.Column(
        db.String(36), db.ForeignKey("edu_contents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    schema_name = db.Column(db.String(100), nullable=False)
    schema_version = db.Column(db.String(30), nullable=False, default="1.0")
    source_json = db.Column(db.JSON, nullable=False)
    rendered_html = db.Column(db.Text)
    parent_version_id = db.Column(db.String(36))
    change_summary = db.Column(db.String(500), nullable=False, default="")
    created_by_user_id = db.Column(db.String(100), nullable=False)
    source_agent_run_id = db.Column(db.String(100))
    checksum = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class EducationMaterial(TimestampMixin, db.Model):
    __tablename__ = "edu_materials"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lesson_id = db.Column(
        db.String(36), db.ForeignKey("edu_lessons.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    owner_user_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    storage_path = db.Column(db.String(1000), nullable=True)
    asset_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")


class PublishedLessonVersion(db.Model):
    __tablename__ = "edu_published_lesson_versions"
    __table_args__ = (
        db.UniqueConstraint("lesson_id", "version_number", name="uq_edu_lesson_publish_version"),
        db.UniqueConstraint("lesson_id", "idempotency_key", name="uq_edu_lesson_publish_key"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    lesson_id = db.Column(
        db.String(36), db.ForeignKey("edu_lessons.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    lesson_plan_version_id = db.Column(db.String(36))
    student_release_manifest = db.Column(db.JSON, nullable=False)
    teacher_evaluation_manifest = db.Column(db.JSON, nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False)
    published_by = db.Column(db.String(100), nullable=False)
    published_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="active")


class Assignment(TimestampMixin, db.Model):
    __tablename__ = "edu_assignments"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lesson_id = db.Column(
        db.String(36), db.ForeignKey("edu_lessons.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    instruction_json = db.Column(db.JSON, nullable=False)
    evaluation_json = db.Column(db.JSON, nullable=False, default=dict)
    max_attempts = db.Column(db.Integer, nullable=False, default=1)
    allow_revision_after_feedback = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(20), nullable=False, default="draft")
    published_by = db.Column(db.String(100))
    published_at = db.Column(db.DateTime)


class Submission(TimestampMixin, db.Model):
    __tablename__ = "edu_submissions"
    __table_args__ = (
        db.UniqueConstraint("assignment_id", "student_user_id", name="uq_edu_assignment_student"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    assignment_id = db.Column(
        db.String(36), db.ForeignKey("edu_assignments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    student_user_id = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="draft")
    current_version_id = db.Column(db.String(36))
    draft_answer_json = db.Column(db.JSON)
    draft_artifact_ids = db.Column(db.JSON)
    draft_updated_at = db.Column(db.DateTime)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    submitted_at = db.Column(db.DateTime)
    final_score = db.Column(db.Float)
    graded_by = db.Column(db.String(100))
    graded_at = db.Column(db.DateTime)


class SubmissionVersion(db.Model):
    __tablename__ = "edu_submission_versions"
    __table_args__ = (
        db.UniqueConstraint("submission_id", "version_number", name="uq_edu_submission_version"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    submission_id = db.Column(
        db.String(36), db.ForeignKey("edu_submissions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    answer_json = db.Column(db.JSON, nullable=False)
    artifact_ids = db.Column(db.JSON, nullable=False, default=list)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    source_version_id = db.Column(db.String(36))
    checksum = db.Column(db.String(64), nullable=False)


class Feedback(db.Model):
    __tablename__ = "edu_feedback"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    submission_version_id = db.Column(
        db.String(36), db.ForeignKey("edu_submission_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    feedback_json = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="released")
    score = db.Column(db.Float)
    released_by = db.Column(db.String(100), nullable=False)
    released_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class LearningEvent(db.Model):
    __tablename__ = "edu_learning_events"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36), db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_user_id = db.Column(db.String(100), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    object_type = db.Column(db.String(50), nullable=False)
    object_id = db.Column(db.String(36), nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
