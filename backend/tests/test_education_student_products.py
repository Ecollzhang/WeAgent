from datetime import timedelta
from io import BytesIO

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class StudentProductTestConfig:
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
    EDUCATION_MAX_UPLOAD_BYTES = 1024 * 1024


@pytest.fixture()
def app():
    from services.edu.app import create_edu_app

    application = create_edu_app(StudentProductTestConfig)
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


def auth(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def setup_course(client, app):
    teacher = auth(app, "teacher")
    student = auth(app, "student")
    course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "English reading evidence",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": "Reading and writing",
        },
    ).get_json()
    invitation = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers=teacher,
        json={},
    ).get_json()
    assert client.post(
        "/api/edu/invitations/accept",
        headers=student,
        json={"token": invitation["token"]},
    ).status_code == 200
    return teacher, student, course


def publish_question(
    client,
    teacher,
    course_id,
    *,
    title,
    point,
    correct_answer,
):
    item = client.post(
        f"/api/edu/courses/{course_id}/questions",
        headers=teacher,
        json={
            "title": title,
            "question_type": "single_choice",
            "prompt": f"Question about {point}",
            "options": ["First", "Second", "Third", "Fourth"],
            "difficulty": "easy",
            "score": 5,
            "knowledge_points": [point],
            "correct_answer": correct_answer,
            "explanation": f"Evidence for {point}",
        },
    ).get_json()
    assert client.post(
        f"/api/edu/questions/{item['id']}/publish",
        headers=teacher,
    ).status_code == 200
    return item


def test_student_generates_submits_mock_exam_and_receives_evidence(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    first = publish_question(
        client,
        teacher,
        course["id"],
        title="Emotion",
        point="emotion inference",
        correct_answer="C",
    )
    second = publish_question(
        client,
        teacher,
        course["id"],
        title="Detail",
        point="detail retrieval",
        correct_answer="A",
    )

    created = client.post(
        f"/api/edu/courses/{course['id']}/mock-exams",
        headers=student,
        json={
            "title": "My diagnostic",
            "question_count": 2,
            "duration_minutes": 20,
            "difficulty_mix": {"easy": 2},
        },
    )

    assert created.status_code == 201
    attempt = created.get_json()
    assert attempt["status"] == "in_progress"
    assert len(attempt["questions"]) == 2
    assert all("answer" not in question for question in attempt["questions"])
    question_ids = {
        question["item_id"]: question["id"] for question in attempt["questions"]
    }

    saved = client.put(
        f"/api/edu/mock-exams/{attempt['id']}/answers",
        headers=student,
        json={
            "answers": {
                question_ids[first["id"]]: "A",
                question_ids[second["id"]]: "A",
            }
        },
    )
    assert saved.status_code == 200
    submitted = client.post(
        f"/api/edu/mock-exams/{attempt['id']}/submit",
        headers=student,
    )

    assert submitted.status_code == 200
    result = submitted.get_json()
    assert result["status"] == "submitted"
    assert result["score"] == 5
    assert result["max_score"] == 10
    assert result["accuracy"] == 0.5
    assert len(result["evidence"]) == 2
    assert {
        row["knowledge_points"][0]: row["correct"] for row in result["evidence"]
    } == {
        "emotion inference": False,
        "detail retrieval": True,
    }


def test_weakness_and_teacher_insight_are_derived_from_attempt_evidence(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    question = publish_question(
        client,
        teacher,
        course["id"],
        title="Emotion",
        point="emotion inference",
        correct_answer="C",
    )
    attempt = client.post(
        f"/api/edu/courses/{course['id']}/mock-exams",
        headers=student,
        json={"question_count": 1, "duration_minutes": 10},
    ).get_json()
    version_id = attempt["questions"][0]["id"]
    client.put(
        f"/api/edu/mock-exams/{attempt['id']}/answers",
        headers=student,
        json={"answers": {version_id: "A"}},
    )
    client.post(
        f"/api/edu/mock-exams/{attempt['id']}/submit",
        headers=student,
    )

    weakness = client.post(
        f"/api/edu/courses/{course['id']}/weakness-analysis",
        headers=student,
    )
    assert weakness.status_code == 201
    payload = weakness.get_json()
    assert payload["data_state"] == "ready"
    assert payload["weaknesses"][0]["knowledge_point"] == "emotion inference"
    assert payload["weaknesses"][0]["wrong_count"] == 1
    assert payload["evidence"][0]["attempt_id"] == attempt["id"]
    assert payload["recommendations"][0]["knowledge_point"] == "emotion inference"

    refreshed = client.post(
        f"/api/edu/courses/{course['id']}/student-insights/refresh",
        headers=teacher,
    )
    assert refreshed.status_code == 201
    insights = refreshed.get_json()["items"]
    student_insight = next(
        row for row in insights if row["student_user_id"] == "student"
    )
    assert student_insight["data_state"] == "ready"
    assert student_insight["summary"]["accuracy"] == 0
    assert student_insight["summary"]["evidence_count"] == 1
    assert student_insight["evidence"][0]["object_id"] == attempt["id"]

    assert client.get(
        f"/api/edu/courses/{course['id']}/student-insights",
        headers=student,
    ).status_code == 404


def test_student_mind_map_is_versioned_editable_and_source_linked(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    asset = client.post(
        f"/api/edu/courses/{course['id']}/assets",
        headers=teacher,
        data={
            "title": "Narrative source",
            "purpose": "knowledge_resource",
            "visibility_scope": "course_published",
            "file": (BytesIO(b"source"), "source.pdf"),
        },
        content_type="multipart/form-data",
    ).get_json()
    resource = client.post(
        f"/api/edu/courses/{course['id']}/knowledge-resources",
        headers=teacher,
        json={
            "asset_id": asset["id"],
            "title": "Narrative evidence",
            "visibility_scope": "course_published",
        },
    ).get_json()

    generated = client.post(
        f"/api/edu/courses/{course['id']}/mind-maps",
        headers=student,
        json={"title": "My course map"},
    )
    assert generated.status_code == 201
    mind_map = generated.get_json()
    assert mind_map["current_version"]["version_number"] == 1
    assert mind_map["current_version"]["tree"]["label"] == course["title"]
    assert resource["id"] in mind_map["current_version"]["source_refs"]

    edited_tree = {
        "id": "root",
        "label": "My edited map",
        "children": [
            {
                "id": "focus",
                "label": "Narrative focus",
                "children": [],
                "source_ref": resource["id"],
            }
        ],
    }
    edited = client.post(
        f"/api/edu/mind-maps/{mind_map['id']}/versions",
        headers=student,
        json={
            "tree": edited_tree,
            "source_refs": [resource["id"]],
            "change_summary": "Focus my review",
        },
    )
    assert edited.status_code == 201
    assert edited.get_json()["current_version"]["version_number"] == 2
    assert edited.get_json()["current_version"]["tree"]["label"] == "My edited map"

    outsider = auth(app, "outsider")
    assert client.get(
        f"/api/edu/mind-maps/{mind_map['id']}",
        headers=outsider,
    ).status_code == 404


def test_teacher_insight_reports_insufficient_data_without_fabricated_scores(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)

    response = client.post(
        f"/api/edu/courses/{course['id']}/student-insights/refresh",
        headers=teacher,
    )

    assert response.status_code == 201
    insight = next(
        row for row in response.get_json()["items"]
        if row["student_user_id"] == "student"
    )
    assert insight["data_state"] == "insufficient"
    assert insight["summary"]["accuracy"] is None
    assert insight["summary"]["evidence_count"] == 0
    assert insight["weaknesses"] == []

