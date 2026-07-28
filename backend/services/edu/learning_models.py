"""Student product and evidence-backed insight persistence."""

from datetime import datetime

from .extensions import db
from .models import TimestampMixin, new_id


class MockExamAttempt(TimestampMixin, db.Model):
    __tablename__ = "edu_mock_exam_attempts"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paper_version_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assessment_paper_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_user_id = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="in_progress", index=True)
    answers_json = db.Column(db.JSON, nullable=False, default=dict)
    evidence_json = db.Column(db.JSON, nullable=False, default=list)
    score = db.Column(db.Float, nullable=True)
    max_score = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)


class WeaknessAnalysisSnapshot(db.Model):
    __tablename__ = "edu_weakness_snapshots"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_user_id = db.Column(db.String(100), nullable=False, index=True)
    data_state = db.Column(db.String(20), nullable=False)
    evidence = db.Column(db.JSON, nullable=False, default=list)
    weaknesses = db.Column(db.JSON, nullable=False, default=list)
    recommendations = db.Column(db.JSON, nullable=False, default=list)
    source_fingerprint = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CourseMindMap(TimestampMixin, db.Model):
    __tablename__ = "edu_course_mind_maps"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    current_version_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)


class CourseMindMapVersion(db.Model):
    __tablename__ = "edu_course_mind_map_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "mind_map_id",
            "version_number",
            name="uq_edu_course_mind_map_version",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    mind_map_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_course_mind_maps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    tree_json = db.Column(db.JSON, nullable=False)
    source_refs = db.Column(db.JSON, nullable=False, default=list)
    change_summary = db.Column(db.String(500), nullable=False, default="")
    checksum = db.Column(db.String(64), nullable=False)
    created_by_user_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class StudentInsightSnapshot(db.Model):
    __tablename__ = "edu_student_insight_snapshots"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_user_id = db.Column(db.String(100), nullable=False, index=True)
    data_state = db.Column(db.String(20), nullable=False)
    summary_json = db.Column(db.JSON, nullable=False, default=dict)
    evidence_json = db.Column(db.JSON, nullable=False, default=list)
    weaknesses_json = db.Column(db.JSON, nullable=False, default=list)
    recommendations_json = db.Column(db.JSON, nullable=False, default=list)
    generated_by_user_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

