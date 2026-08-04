"""Persisted Education workflow definitions."""

from datetime import datetime

from .extensions import db
from .models import new_id


def product_business_route(product_code, course_id, lesson_id=None, options=None):
    options = options if isinstance(options, dict) else {}
    query = {"courseId": course_id}
    if lesson_id:
        query["lessonId"] = lesson_id
    routes = {
        "roster_import": f"/education/courses/{course_id}",
        "courseware": "/education/teacher/courseware",
        "question_generation": f"/education/courses/{course_id}/knowledge",
        "paper_generation": f"/education/courses/{course_id}/knowledge",
        "knowledge_research": f"/education/courses/{course_id}/knowledge",
        "student_insight": "/education/teacher/insights",
        "submission_review": (
            f"/education/courses/{course_id}/assignments/"
            f"{options.get('assignment_id')}/review/{options.get('submission_id')}"
        ),
        "mock_exam": "/education/student/mock-exams",
        "weakness_analysis": f"/education/courses/{course_id}",
        "course_mind_map": "/education/student/mind-maps",
    }
    if product_code == "roster_import":
        query["tab"] = "people"
    elif product_code == "weakness_analysis":
        query["tab"] = "weaknesses"
    return {"path": routes.get(product_code, f"/education/courses/{course_id}"), "query": query}


PRODUCT_ADOPTED_OBJECTS = {
    "product.roster_import": (
        "edu.course.members.import",
        "course_roster",
        "roster",
    ),
    "product.courseware": (
        "edu.courseware.create",
        "courseware",
        "slide_document",
    ),
    "product.question_generation": (
        "edu.question_bank.upsert",
        "question_bank",
        "question_bank",
    ),
    "product.paper_generation": (
        "edu.paper.compose",
        "assessment_paper",
        "assessment_paper",
    ),
    "product.knowledge_research": (
        "edu.knowledge.resource.adopt",
        "knowledge_resource",
        "knowledge_resource",
    ),
    "product.student_insight": (
        "edu.student_insight.refresh",
        "student_insight_report",
        "student_insight",
    ),
    "product.submission_review": (
        "edu.submission_review.analysis.create",
        "submission_review_analysis",
        "review_analysis",
    ),
    "product.mock_exam": (
        "edu.mock_exam.create",
        "mock_exam",
        "mock_exam",
    ),
    "product.weakness_analysis": (
        "edu.weakness.analyze",
        "weakness_analysis",
        "weakness_analysis",
    ),
    "product.course_mind_map": (
        "edu.mind_map.create",
        "course_mind_map",
        "mind_map",
    ),
}


def adopted_object_from_tool_result(
    *,
    workflow_code,
    tool_name,
    result,
    course_id,
    lesson_id=None,
    tool_call_id=None,
):
    contract = PRODUCT_ADOPTED_OBJECTS.get(str(workflow_code or ""))
    if not contract or contract[0] != tool_name:
        return None
    product_code = str(workflow_code).split(".", 1)[1]
    payload = result if isinstance(result, dict) else {}
    if product_code == "courseware":
        content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
        version = payload.get("version") if isinstance(payload.get("version"), dict) else {}
        object_id = content.get("id")
        version_id = version.get("id") or content.get("current_version_id")
    else:
        object_id = payload.get("id") or course_id
        version_id = (
            payload.get("current_version_id")
            or payload.get("version_id")
            or tool_call_id
        )
    if not object_id or not version_id:
        return None
    return {
        "domain": "edu",
        "object_type": contract[1],
        "object_id": str(object_id),
        "version_id": str(version_id),
        "preview_kind": contract[2],
        "business_route": product_business_route(
            product_code,
            course_id,
            lesson_id,
            payload,
        ),
    }


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
        product_code = (
            str(self.workflow_code or "").split(".", 1)[1]
            if str(self.workflow_code or "").startswith("product.")
            else None
        )
        nodes = self.nodes or []
        agent_nodes = [node for node in nodes if node.get("type") == "agent_task"]
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
            "nodes": nodes,
            "input_payload": self.input_payload or {},
            "output": self.output or {},
            "error_summary": self.error_summary,
            "product_code": product_code,
            "business_route": (
                product_business_route(
                    product_code,
                    self.course_id,
                    self.lesson_id,
                    (
                        (self.input_payload or {}).get("options")
                        if product_code == "submission_review"
                        else None
                    ),
                )
                if product_code
                else None
            ),
            "agent_count": len(agent_nodes),
            "completed_agent_count": len(
                [node for node in agent_nodes if node.get("status") == "done"]
            ),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EducationConversationBinding(db.Model):
    """Durable Education context for one core conversation.

    The role snapshot is audit/UI data only. Every executable request must
    re-resolve the live CourseMembership.
    """

    __tablename__ = "edu_conversation_bindings"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    conversation_id = db.Column(
        db.String(36), nullable=False, unique=True, index=True
    )
    actor_user_id = db.Column(db.String(100), nullable=False, index=True)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey("edu_courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id = db.Column(db.String(36), nullable=True, index=True)
    membership_role_snapshot = db.Column(db.String(20), nullable=True)
    binding_mode = db.Column(db.String(30), nullable=False, default="manual")
    material_policy = db.Column(
        db.String(30), nullable=False, default="course_only"
    )
    agent_service_views = db.Column(db.JSON, nullable=False, default=dict)
    source_route = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "actor_user_id": self.actor_user_id,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "membership_role_snapshot": self.membership_role_snapshot,
            "binding_mode": self.binding_mode,
            "material_policy": self.material_policy,
            "agent_service_views": self.agent_service_views or {},
            "source_route": self.source_route,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
