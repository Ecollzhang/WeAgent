from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class EducationChatConfig:
    TESTING = True
    SERVICE_NAME = "weagent-edu-chat-test"
    PORT = 5102
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True
    EDUCATION_CHAT_ENABLED = True
    EDUCATION_CHAT_MANUAL_CREATE = True
    EDUCATION_CHAT_TOOLS_ENABLED = True
    EDUCATION_RAG_ENABLED = True


class FakeCoreRuntime:
    def __init__(self):
        self.created = []
        self.deleted = []

    def create_conversation(self, **kwargs):
        self.created.append(kwargs)
        return {
            "id": f"conversation-{len(self.created)}",
            "title": kwargs["title"],
            "services": kwargs["services"],
            "kb_domain": "edu",
            "workspace_id": "workspace-edu",
        }

    def delete_conversation(self, *, authorization, conversation_id):
        self.deleted.append((authorization, conversation_id))


@pytest.fixture()
def education_app():
    from services.edu.app import create_edu_app

    app = create_edu_app(EducationChatConfig)
    runtime = FakeCoreRuntime()
    app.extensions["education_runtime_client"] = runtime
    with app.app_context():
        db.create_all()
    yield app, runtime
    with app.app_context():
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_course(client, headers, title):
    response = client.post(
        "/api/edu/courses",
        headers=headers,
        json={
            "title": title,
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
        },
    )
    assert response.status_code == 201
    return response.get_json()


def add_student(client, teacher_headers, student_headers, course_id):
    invitation = client.post(
        f"/api/edu/courses/{course_id}/invitations",
        headers=teacher_headers,
        json={},
    ).get_json()
    response = client.post(
        "/api/edu/invitations/accept",
        headers=student_headers,
        json={"token": invitation["token"]},
    )
    assert response.status_code == 200


def test_conversation_options_return_renderable_trusted_agent_metadata(
    education_app,
):
    app, _runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    course = create_course(client, teacher, "Renderable Agent Course")

    response = client.get(
        f"/api/edu/conversations/options?course_id={course['id']}",
        headers=teacher,
    )

    assert response.status_code == 200
    agents = response.get_json()["agents"]
    courseware_agent = next(item for item in agents if item["id"] == "_edu_2")
    assert courseware_agent["name"] == "课件制作师"
    assert courseware_agent["category_id"] == "cat_edu_ware"
    assert courseware_agent["category_name"] == "课件制作"
    assert courseware_agent["avatar_color"] == "#22c55e"
    assert courseware_agent["adapter_name"] == "claude"


def test_failed_core_bootstrap_revokes_the_persisted_runtime_grant(
    education_app,
):
    from services.edu.runtime_client import CoreRuntimeError
    from services.edu.tool_models import EducationToolGrant

    app, runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    course = create_course(client, teacher, "Failed Runtime Course")

    def reject_runtime(**_kwargs):
        raise CoreRuntimeError("runtime unavailable")

    runtime.create_conversation = reject_runtime
    response = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={"course_id": course["id"], "agent_ids": ["_edu_2"]},
    )

    assert response.status_code == 503
    with app.app_context():
        grant = EducationToolGrant.query.one()
        assert grant.status == "revoked"
        assert grant.revoked_at is not None


def test_bootstrap_uses_membership_role_and_agent_service_views(education_app):
    app, runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    student = auth_headers(app, "student")
    course = create_course(client, teacher, "Narrative Reading")
    add_student(client, teacher, student, course["id"])

    response = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={
            "course_id": course["id"],
            "agent_ids": ["_edu_2", "_edu_9"],
            "material_policy": "authorized_knowledge",
            "role": "student",
            "services": ["rd", "office"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["context"]["membership_role"] == "teacher"
    assert payload["binding"]["membership_role_snapshot"] == "teacher"
    assert payload["binding"]["course_id"] == course["id"]
    assert payload["agent_service_views"] == {
        "_edu_2": ["edu", "rag"],
        "_edu_9": ["edu"],
    }
    assert payload["conversation"]["services"] == ["edu", "rag"]
    assert runtime.created[0]["workspace_role"] == "teacher"
    assert runtime.created[0]["agent_service_views"] == payload["agent_service_views"]
    assert len(runtime.created[0]["education_run_grant"]) >= 40
    assert "role" not in runtime.created[0]["visible_context"]
    assert "services" not in runtime.created[0]["visible_context"]


def test_student_cannot_select_teacher_agent_or_forge_role(education_app):
    app, runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    student = auth_headers(app, "student")
    course = create_course(client, teacher, "Student Course")
    add_student(client, teacher, student, course["id"])

    forbidden = client.post(
        "/api/edu/conversations/bootstrap",
        headers=student,
        json={
            "course_id": course["id"],
            "agent_ids": ["_edu_2"],
            "role": "teacher",
        },
    )
    allowed = client.post(
        "/api/edu/conversations/bootstrap",
        headers=student,
        json={
            "course_id": course["id"],
            "agent_ids": ["_edu_7"],
            "role": "teacher",
        },
    )

    assert forbidden.status_code == 403
    assert forbidden.get_json()["error_code"] == "agent_role_mismatch"
    assert allowed.status_code == 201
    assert allowed.get_json()["context"]["membership_role"] == "student"
    assert runtime.created[-1]["workspace_role"] == "student"


def test_switching_courses_re_resolves_membership_role(education_app):
    app, _runtime = education_app
    client = app.test_client()
    mixed_user = auth_headers(app, "mixed")
    other_teacher = auth_headers(app, "other-teacher")
    teacher_course = create_course(client, mixed_user, "Teacher Course")
    student_course = create_course(client, other_teacher, "Student Course")
    add_student(client, other_teacher, mixed_user, student_course["id"])

    teacher_response = client.post(
        "/api/edu/conversations/bootstrap",
        headers=mixed_user,
        json={"course_id": teacher_course["id"], "agent_ids": ["_edu_1"]},
    )
    student_response = client.post(
        "/api/edu/conversations/bootstrap",
        headers=mixed_user,
        json={"course_id": student_course["id"], "agent_ids": ["_edu_5"]},
    )

    assert teacher_response.status_code == 201
    assert teacher_response.get_json()["context"]["membership_role"] == "teacher"
    assert student_response.status_code == 201
    assert student_response.get_json()["context"]["membership_role"] == "student"


def test_course_bootstrap_is_the_only_no_course_conversation_and_binds_on_create(
    education_app,
):
    from services.edu.workflow_models import EducationConversationBinding

    app, runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")

    rejected = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={"agent_ids": ["_edu_1"]},
    )
    assert rejected.status_code == 400

    created = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={
            "binding_mode": "course_bootstrap",
            "agent_ids": ["_edu_1"],
            "source_route": {"path": "/education"},
        },
    )
    assert created.status_code == 201
    payload = created.get_json()
    assert payload["binding"]["course_id"] is None
    assert payload["binding"]["binding_mode"] == "course_bootstrap"
    assert payload["context"]["membership_role"] == "course_creator"
    assert payload["agent_service_views"] == {"_edu_1": ["edu"]}
    assert runtime.created[-1]["workspace_role"] == "course_creator"

    grant = runtime.created[-1]["education_run_grant"]
    adopted = client.post(
        "/api/edu/tools/edu.course.create/invoke",
        headers={"X-Education-Run-Grant": grant},
        json={
            "agent_id": "_edu_1",
            "idempotency_key": "create-course-from-bootstrap",
            "arguments": {
                "title": "Agent Created Course",
                "subject_code": "high_school_english",
                "grade_band": "senior_high",
            },
        },
    )
    assert adopted.status_code == 200
    course = adopted.get_json()["result"]
    with app.app_context():
        binding = EducationConversationBinding.query.filter_by(
            conversation_id=payload["conversation"]["id"]
        ).one()
        assert binding.course_id == course["id"]
        assert binding.membership_role_snapshot == "teacher"
        assert binding.binding_mode == "course_bootstrap"


def test_context_revalidates_membership_and_returns_binding(education_app):
    app, _runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    course = create_course(client, teacher, "Context Course")
    created = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={"course_id": course["id"], "agent_ids": ["_edu_1"]},
    ).get_json()

    context = client.get(
        f"/api/edu/conversations/{created['conversation']['id']}/context",
        headers=teacher,
    )

    assert context.status_code == 200
    payload = context.get_json()
    assert payload["course"]["id"] == course["id"]
    assert payload["course"]["membership_role"] == "teacher"
    assert payload["binding"]["status"] == "active"
    assert payload["agent_service_views"]["_edu_1"] == ["edu", "rag"]


def test_core_runtime_can_rotate_a_conversation_grant_without_exposing_it_to_user(
    education_app,
):
    from services.edu.tool_models import EducationToolGrant

    app, _runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    course = create_course(client, teacher, "Durable Runtime Course")
    created = client.post(
        "/api/edu/conversations/bootstrap",
        headers=teacher,
        json={
            "course_id": course["id"],
            "agent_ids": ["_edu_1", "_edu_2"],
            "material_policy": "authorized_knowledge",
        },
    ).get_json()
    conversation_id = created["conversation"]["id"]

    denied = client.post(
        f"/api/edu/conversations/{conversation_id}/runtime-grant",
        headers=teacher,
    )
    assert denied.status_code == 403

    with app.app_context():
        service_token = create_access_token(
            identity="weagent-core-runtime",
            additional_claims={
                "service": "core",
                "actor_user_id": "teacher",
            },
            expires_delta=timedelta(minutes=2),
        )
    rotated = client.post(
        f"/api/edu/conversations/{conversation_id}/runtime-grant",
        headers={"Authorization": f"Bearer {service_token}"},
    )

    assert rotated.status_code == 201
    payload = rotated.get_json()
    assert len(payload["run_grant"]) >= 40
    assert payload["membership_role"] == "teacher"
    assert payload["agent_service_views"] == {
        "_edu_1": ["edu", "rag"],
        "_edu_2": ["edu", "rag"],
    }
    assert payload["services"] == ["edu", "rag"]
    with app.app_context():
        grants = EducationToolGrant.query.filter_by(
            conversation_id=conversation_id
        ).order_by(EducationToolGrant.created_at.asc()).all()
        assert [grant.status for grant in grants] == ["revoked", "active"]
        assert grants[-1].agent_ids == ["_edu_1", "_edu_2"]


def test_schema_migration_backfills_historical_product_conversation_binding(
    education_app,
):
    from services.edu.schema_maintenance import (
        migrate_existing_education_schema,
    )
    from services.edu.workflow_models import (
        EducationAgentRun,
        EducationConversationBinding,
    )

    app, _runtime = education_app
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    course = create_course(client, teacher, "Historical Course")
    with app.app_context():
        db.session.add(
            EducationAgentRun(
                course_id=course["id"],
                requested_by="teacher",
                workflow_code="product.courseware",
                workflow_name="Historical courseware",
                status="completed",
                conversation_id="historical-conversation",
                nodes=[
                    {
                        "id": "design",
                        "type": "agent_task",
                        "agent_id": "_edu_1",
                    },
                    {
                        "id": "slides",
                        "type": "agent_task",
                        "agent_id": "_edu_2",
                    },
                ],
                input_payload={},
                output={},
            )
        )
        db.session.commit()

        changes = migrate_existing_education_schema()

        binding = EducationConversationBinding.query.filter_by(
            conversation_id="historical-conversation"
        ).one()
        assert binding.course_id == course["id"]
        assert binding.actor_user_id == "teacher"
        assert binding.membership_role_snapshot == "teacher"
        assert binding.binding_mode == "product"
        assert binding.agent_service_views == {
            "_edu_1": ["edu", "rag"],
            "_edu_2": ["edu", "rag"],
        }
        assert binding.source_route["path"] == "/education/teacher/courseware"
        assert "edu_conversation_bindings.backfilled:1" in changes


def test_education_service_exposes_safe_spec_and_chat_flags(education_app):
    app, _runtime = education_app
    client = app.test_client()

    response = client.get("/api/edu/spec")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["domain"] == "edu"
    assert payload["capabilities"]["chat"] is True
    assert payload["endpoints"]["conversation_bootstrap"]["method"] == "POST"
    assert "base_url" not in payload
