from datetime import timedelta
from io import BytesIO

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class KnowledgeCenterTestConfig:
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

    application = create_edu_app(KnowledgeCenterTestConfig)
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


def course_with_student(client, app):
    teacher = auth(app, "teacher")
    student = auth(app, "student")
    course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "English evidence lab",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": "Evidence-based reading",
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


def question_payload():
    return {
        "title": "Narrative emotion",
        "question_type": "single_choice",
        "prompt": "What is the narrator's primary emotion?",
        "options": [
            "Excitement only",
            "Nervousness only",
            "Mixed excitement and nervousness",
            "Complete confidence",
        ],
        "difficulty": "easy",
        "score": 5,
        "knowledge_points": ["emotion inference", "text evidence"],
        "correct_answer": "C",
        "explanation": "The passage explicitly contains both emotions.",
    }


def test_question_versions_are_canonical_and_answers_are_teacher_private(app):
    client = app.test_client()
    teacher, student, course = course_with_student(client, app)

    invalid = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json={
            **question_payload(),
            "options": ["A. One", "B. Two", "C. Three", "D. Four"],
        },
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["error_code"] == "non_canonical_options"

    created = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json=question_payload(),
    )
    assert created.status_code == 201
    question = created.get_json()
    assert question["current_version"]["options"][0] == "Excitement only"
    assert question["current_version"]["answer"]["correct_answer"] == "C"

    assert client.get(
        f"/api/edu/courses/{course['id']}/questions",
        headers=student,
    ).get_json()["items"] == []

    published = client.post(
        f"/api/edu/questions/{question['id']}/publish",
        headers=teacher,
    )
    assert published.status_code == 200
    student_items = client.get(
        f"/api/edu/courses/{course['id']}/questions",
        headers=student,
    ).get_json()["items"]
    assert len(student_items) == 1
    assert "answer" not in student_items[0]["current_version"]

    version = client.post(
        f"/api/edu/questions/{question['id']}/versions",
        headers=teacher,
        json={**question_payload(), "difficulty": "medium"},
    )
    assert version.status_code == 201
    assert version.get_json()["current_version"]["version_number"] == 2
    assert question["current_version"]["id"] != version.get_json()["current_version"]["id"]


def test_paper_version_freezes_question_versions_and_student_sees_published_paper(app):
    client = app.test_client()
    teacher, student, course = course_with_student(client, app)
    question = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json=question_payload(),
    ).get_json()
    client.post(f"/api/edu/questions/{question['id']}/publish", headers=teacher)

    composed = client.post(
        f"/api/edu/courses/{course['id']}/papers/compose",
        headers=teacher,
        json={
            "title": "Unit diagnostic",
            "purpose": "mock_exam",
            "duration_minutes": 20,
            "item_ids": [question["id"]],
        },
    )

    assert composed.status_code == 201
    paper = composed.get_json()
    assert paper["current_version"]["item_version_ids"] == [
        question["current_version"]["id"]
    ]
    assert paper["current_version"]["total_score"] == 5
    assert client.get(
        f"/api/edu/courses/{course['id']}/papers",
        headers=student,
    ).get_json()["items"] == []

    assert client.post(
        f"/api/edu/papers/{paper['id']}/publish",
        headers=teacher,
    ).status_code == 200
    student_papers = client.get(
        f"/api/edu/courses/{course['id']}/papers",
        headers=student,
    ).get_json()["items"]
    assert len(student_papers) == 1
    assert student_papers[0]["current_version"]["item_version_ids"] == [
        question["current_version"]["id"]
    ]


def test_knowledge_resource_references_durable_asset_and_summary(app):
    client = app.test_client()
    teacher, student, course = course_with_student(client, app)
    asset = client.post(
        f"/api/edu/courses/{course['id']}/assets",
        headers=teacher,
        data={
            "title": "Reading source",
            "purpose": "knowledge_resource",
            "visibility_scope": "course_published",
            "file": (BytesIO(b"published-source"), "source.pdf"),
        },
        content_type="multipart/form-data",
    ).get_json()

    created = client.post(
        f"/api/edu/courses/{course['id']}/knowledge-resources",
        headers=teacher,
        json={
            "asset_id": asset["id"],
            "title": "Narrative reading source",
            "resource_type": "reference",
            "visibility_scope": "course_published",
        },
    )
    assert created.status_code == 201
    resource = created.get_json()
    assert resource["ingestion_status"] == "pending"
    assert resource["asset"]["id"] == asset["id"]

    student_resources = client.get(
        f"/api/edu/courses/{course['id']}/knowledge-resources",
        headers=student,
    )
    assert student_resources.status_code == 200
    assert student_resources.get_json()["items"][0]["asset"]["download_url"] == asset["download_url"]

    summary = client.get(
        f"/api/edu/courses/{course['id']}/knowledge-center",
        headers=teacher,
    )
    assert summary.status_code == 200
    assert summary.get_json()["counts"] == {
        "questions": 0,
        "papers": 0,
        "knowledge_resources": 1,
    }

