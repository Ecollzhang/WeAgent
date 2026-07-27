from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class EducationWorkflowTestConfig:
    TESTING = True
    SERVICE_NAME = "weagent-edu-test"
    PORT = 5102
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True


@pytest.fixture()
def education_app():
    from services.edu.app import create_edu_app

    app = create_edu_app(EducationWorkflowTestConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def headers(app, user):
    with app.app_context():
        token = create_access_token(identity=user)
    return {"Authorization": f"Bearer {token}"}


def course_with_student(app):
    client = app.test_client()
    teacher = headers(app, "teacher")
    student = headers(app, "student")
    course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Reading and Writing",
            "subject_code": "primary_chinese",
            "grade_band": "primary",
        },
    ).get_json()
    invitation = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers=teacher,
        json={},
    ).get_json()
    client.post(
        "/api/edu/invitations/accept",
        headers=student,
        json={"token": invitation["token"]},
    )
    return course, teacher, student


def test_subject_packs_expose_distinct_genre_and_lesson_plan_focus(education_app):
    client = education_app.test_client()
    auth = headers(education_app, "teacher")

    response = client.get("/api/edu/subject-packs", headers=auth)

    assert response.status_code == 200
    packs = {item["subject_code"]: item for item in response.get_json()["items"]}
    assert "narrative" in packs["primary_chinese"]["text_genres"]
    assert "expository" in packs["high_school_english"]["text_genres"]
    assert packs["primary_chinese"]["lesson_plan_sections"]
    assert packs["high_school_english"]["lesson_plan_sections"]
    assert (
        packs["primary_chinese"]["text_genres"]["scenery"]["teaching_focus"]
        != packs["primary_chinese"]["text_genres"]["narrative"]["teaching_focus"]
    )


def test_system_workflows_cover_teacher_and_student_agent_teams(education_app):
    client = education_app.test_client()
    auth = headers(education_app, "teacher")

    agents = client.get("/api/edu/agent-roles", headers=auth).get_json()["items"]
    templates = client.get("/api/edu/workflow-templates", headers=auth).get_json()["items"]

    role_codes = {item["code"] for item in agents}
    assert {
        "course_designer",
        "courseware_maker",
        "exercise_generator",
        "learning_analyst",
        "learning_planner",
        "note_organizer",
        "practice_coach",
    } <= role_codes
    assert len(templates) >= 8
    assert any(item["code"] == "teacher_lesson_preparation" for item in templates)
    assert any(item["code"] == "student_diagnosis_plan" for item in templates)


def test_teacher_can_save_guided_dag_but_student_cannot(education_app):
    client = education_app.test_client()
    course, teacher, student = course_with_student(education_app)
    payload = {
        "name": "My reading workflow",
        "scope": "course",
        "execution_mode": "guided",
        "nodes": [
            {"id": "design", "type": "agent_task", "agent_role": "course_designer"},
            {"id": "review", "type": "validation", "action": "teaching_review"},
            {"id": "approval", "type": "approval", "gate": "teacher_publish"},
        ],
        "edges": [
            {"from": "design", "to": "review"},
            {"from": "review", "to": "approval"},
        ],
    }

    created = client.post(
        f"/api/edu/courses/{course['id']}/workflows",
        headers=teacher,
        json=payload,
    )
    denied = client.post(
        f"/api/edu/courses/{course['id']}/workflows",
        headers=student,
        json=payload,
    )

    assert created.status_code == 201
    assert created.get_json()["required_approval_gates"] == ["teacher_publish"]
    assert denied.status_code == 404


@pytest.mark.parametrize(
    "mutation,error_fragment",
    [
        (
            lambda payload: payload["edges"].append({"from": "approval", "to": "design"}),
            "cycle",
        ),
        (
            lambda payload: payload["nodes"].append(
                {"id": "shell", "type": "transform", "code": "rm -rf /"}
            ),
            "executable",
        ),
        (
            lambda payload: payload.update(
                {
                    "nodes": [
                        node for node in payload["nodes"] if node["type"] != "approval"
                    ],
                    "edges": [{"from": "design", "to": "review"}],
                }
            ),
            "teacher_publish",
        ),
    ],
)
def test_workflow_validation_rejects_cycles_code_and_missing_gate(
    education_app, mutation, error_fragment
):
    client = education_app.test_client()
    course, teacher, _ = course_with_student(education_app)
    payload = {
        "name": "Unsafe workflow",
        "scope": "course",
        "execution_mode": "guided",
        "nodes": [
            {"id": "design", "type": "agent_task", "agent_role": "course_designer"},
            {"id": "review", "type": "validation", "action": "teaching_review"},
            {"id": "approval", "type": "approval", "gate": "teacher_publish"},
        ],
        "edges": [
            {"from": "design", "to": "review"},
            {"from": "review", "to": "approval"},
        ],
    }
    mutation(payload)

    response = client.post(
        f"/api/edu/courses/{course['id']}/workflows",
        headers=teacher,
        json=payload,
    )

    assert response.status_code == 400
    assert error_fragment in response.get_json()["error"]
