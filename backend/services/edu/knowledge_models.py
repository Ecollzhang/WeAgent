"""Versioned Question Bank, Paper Bank, and Knowledge Base models."""

from datetime import datetime

from .extensions import db
from .models import TimestampMixin, new_id


class AssessmentItem(TimestampMixin, db.Model):
    __tablename__ = "edu_assessment_items"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    source_type = db.Column(db.String(30), nullable=False, default="teacher")
    source_agent_run_id = db.Column(db.String(100), nullable=True, index=True)
    current_version_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    published_by = db.Column(db.String(100), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)


class AssessmentItemVersion(db.Model):
    __tablename__ = "edu_assessment_item_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "item_id",
            "version_number",
            name="uq_edu_assessment_item_version",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    item_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assessment_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    question_type = db.Column(db.String(30), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False, default=list)
    difficulty = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Float, nullable=False)
    knowledge_points = db.Column(db.JSON, nullable=False, default=list)
    grade_band = db.Column(db.String(50), nullable=True)
    source_context = db.Column(db.JSON, nullable=False, default=dict)
    checksum = db.Column(db.String(64), nullable=False)
    created_by_user_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AssessmentAnswerVersion(db.Model):
    __tablename__ = "edu_assessment_answer_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "item_version_id",
            name="uq_edu_assessment_answer_item_version",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    item_version_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assessment_item_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    correct_answer = db.Column(db.JSON, nullable=False)
    explanation = db.Column(db.Text, nullable=False, default="")
    rubric = db.Column(db.JSON, nullable=False, default=dict)
    created_by_user_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AssessmentPaper(TimestampMixin, db.Model):
    __tablename__ = "edu_assessment_papers"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    purpose = db.Column(db.String(30), nullable=False, default="practice")
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    current_version_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    published_by = db.Column(db.String(100), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)


class AssessmentPaperVersion(db.Model):
    __tablename__ = "edu_assessment_paper_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "paper_id",
            "version_number",
            name="uq_edu_assessment_paper_version",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    paper_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assessment_papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    item_version_ids = db.Column(db.JSON, nullable=False)
    sections = db.Column(db.JSON, nullable=False, default=list)
    total_score = db.Column(db.Float, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    blueprint = db.Column(db.JSON, nullable=False, default=dict)
    checksum = db.Column(db.String(64), nullable=False)
    created_by_user_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class KnowledgeResource(TimestampMixin, db.Model):
    __tablename__ = "edu_knowledge_resources"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(40), nullable=False, default="reference")
    visibility_scope = db.Column(
        db.String(30),
        nullable=False,
        default="course_teacher",
        index=True,
    )
    ingestion_status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    ingestion_error = db.Column(db.String(500), nullable=True)
    rag_scope = db.Column(db.String(200), nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)

