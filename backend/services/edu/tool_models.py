"""Course-scoped Agent tool grants and durable invocation audit records."""

from datetime import datetime

from .extensions import db
from .models import new_id


class EducationToolGrant(db.Model):
    __tablename__ = "edu_tool_grants"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_user_id = db.Column(db.String(100), nullable=False, index=True)
    actor_role = db.Column(db.String(20), nullable=False)
    allowed_tools = db.Column(db.JSON, nullable=False, default=list)
    confirmed_actions = db.Column(db.JSON, nullable=False, default=list)
    capability_ids = db.Column(db.JSON, nullable=False, default=list)
    agent_ids = db.Column(db.JSON, nullable=True)
    lesson_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_run_id = db.Column(db.String(100), nullable=True, index=True)
    conversation_id = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "actor_user_id": self.actor_user_id,
            "actor_role": self.actor_role,
            "allowed_tools": self.allowed_tools or [],
            "confirmed_actions": self.confirmed_actions or [],
            "capability_ids": self.capability_ids or [],
            "agent_ids": self.agent_ids or [],
            "lesson_id": self.lesson_id,
            "agent_run_id": self.agent_run_id,
            "conversation_id": self.conversation_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EducationToolCall(db.Model):
    __tablename__ = "edu_tool_calls"
    __table_args__ = (
        db.UniqueConstraint(
            "grant_id",
            "tool_name",
            "idempotency_key",
            name="uq_edu_tool_call_idempotency",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    grant_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_tool_grants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = db.Column(db.String(36), nullable=True, index=True)
    actor_user_id = db.Column(db.String(100), nullable=False, index=True)
    agent_id = db.Column(db.String(100), nullable=True, index=True)
    tool_name = db.Column(db.String(100), nullable=False, index=True)
    idempotency_key = db.Column(db.String(120), nullable=True)
    input_hash = db.Column(db.String(64), nullable=False)
    sanitized_input = db.Column(db.JSON, nullable=False, default=dict)
    result_json = db.Column(db.JSON, nullable=False, default=dict)
    result_summary = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(20), nullable=False, default="running", index=True)
    error_code = db.Column(db.String(100), nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self, include_input=False, include_result=False):
        payload = {
            "id": self.id,
            "grant_id": self.grant_id,
            "course_id": self.course_id,
            "actor_user_id": self.actor_user_id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "result_summary": self.result_summary or {},
            "error_code": self.error_code,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
        if include_input:
            payload["input"] = self.sanitized_input or {}
        if include_result:
            payload["result"] = self.result_json or {}
        return payload
