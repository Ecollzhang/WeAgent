"""Persisted Education workflow definitions."""

from datetime import datetime

from .extensions import db
from .models import new_id


class EducationWorkflow(db.Model):
    __tablename__ = "edu_workflows"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    schema_version = db.Column(db.String(20), nullable=False, default="1.0")
    scope = db.Column(db.String(20), nullable=False, default="course")
    execution_mode = db.Column(db.String(20), nullable=False, default="guided")
    nodes = db.Column(db.JSON, nullable=False)
    edges = db.Column(db.JSON, nullable=False)
    required_approval_gates = db.Column(db.JSON, nullable=False)
    max_nodes = db.Column(db.Integer, nullable=False, default=30)
    max_retries = db.Column(db.Integer, nullable=False, default=2)
    max_parallelism = db.Column(db.Integer, nullable=False, default=4)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "execution_mode": self.execution_mode,
            "nodes": self.nodes,
            "edges": self.edges,
            "required_approval_gates": self.required_approval_gates,
            "max_nodes": self.max_nodes,
            "max_retries": self.max_retries,
            "max_parallelism": self.max_parallelism,
        }


class EducationAgentRun(db.Model):
    __tablename__ = "edu_agent_runs"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id = db.Column(db.String(36), nullable=True, index=True)
    requested_by = db.Column(db.String(100), nullable=False, index=True)
    workflow_code = db.Column(db.String(100), nullable=False)
    workflow_name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    conversation_id = db.Column(db.String(36), nullable=True, index=True)
    sandbox_session_id = db.Column(db.String(100), nullable=True, index=True)
    core_message_id = db.Column(db.String(36), nullable=True)
    tool_grant_id = db.Column(db.String(36), nullable=True, index=True)
    nodes = db.Column(db.JSON, nullable=False, default=list)
    input_payload = db.Column(db.JSON, nullable=False, default=dict)
    output = db.Column(db.JSON, nullable=False, default=dict)
    error_summary = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "requested_by": self.requested_by,
            "workflow_code": self.workflow_code,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "conversation_id": self.conversation_id,
            "sandbox_session_id": self.sandbox_session_id,
            "core_message_id": self.core_message_id,
            "nodes": self.nodes or [],
            "input_payload": self.input_payload or {},
            "output": self.output or {},
            "error_summary": self.error_summary,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
