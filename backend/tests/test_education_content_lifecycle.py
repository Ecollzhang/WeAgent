from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class EducationContentTestConfig:
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
def app():
    from services.edu.app import create_edu_app
    from services.edu.content_routes import education_content_api

    app = create_edu_app(EducationContentTestConfig)
    if education_content_api.name not in app.blueprints:
        app.register_blueprint(education_content_api, url_prefix="/api/edu")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def course(client, teacher, subject_code="high_school_english", grade_band="senior_high"):
    response = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Reading and writing",
            "subject_code": subject_code,
            "grade_band": grade_band,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def join(client, teacher, student, course_id):
    invitation = client.post(
        f"/api/edu/courses/{course_id}/invitations",
        headers=teacher,
        json={},
    ).get_json()
    response = client.post(
        "/api/edu/invitations/accept",
        headers=student,
        json={"token": invitation["token"]},
    )
    assert response.status_code == 200


def lesson_plan(genre="narrative", subject="high_school_english"):
    return {
        "subject_code": subject,
        "learning_domain": "integrated",
        "text_genre_code": genre,
        "objectives": [
            {"id": "objective-1", "description": "Read for structure and write from evidence"}
        ],
        "stages": [
            {
                "name": "Close reading",
                "duration_minutes": 20,
                "teacher_activity": "Model evidence selection",
                "student_activity": "Annotate and discuss",
                "assessment": "Exit note",
            }
        ],
    }


def test_teacher_builds_versioned_lesson_and_student_only_sees_safe_snapshot(app):
    client = app.test_client()
    teacher = headers(app, "teacher-1")
    student = headers(app, "student-1")
    outsider = headers(app, "outsider")
    created_course = course(client, teacher)
    join(client, teacher, student, created_course["id"])

    unit = client.post(
        f"/api/edu/courses/{created_course['id']}/units",
        headers=teacher,
        json={"title": "Stories and growth", "position": 1},
    )
    assert unit.status_code == 201
    lesson = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "unit_id": unit.get_json()["id"],
            "title": "A turning point",
            "learning_domain": "integrated",
            "theme_code": "growth_and_learning",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    )
    assert lesson.status_code == 201
    lesson_id = lesson.get_json()["id"]

    content = client.post(
        f"/api/edu/lessons/{lesson_id}/contents",
        headers=teacher,
        json={
            "kind": "lesson_plan",
            "schema_name": "lesson_plan_json",
            "source_json": lesson_plan(),
        },
    )
    assert content.status_code == 201
    first = content.get_json()
    second = client.post(
        f"/api/edu/contents/{first['content']['id']}/versions",
        headers=teacher,
        json={
            "schema_name": "lesson_plan_json",
            "source_json": {
                **lesson_plan(),
                "objectives": [
                    {"id": "objective-2", "description": "Draft a narrative turning point"}
                ],
            },
            "change_summary": "Narrow the writing objective",
        },
    )
    assert second.status_code == 201
    assert second.get_json()["version"]["version_number"] == 2
    assert second.get_json()["version"]["parent_version_id"] == first["version"]["id"]

    activity = client.post(
        f"/api/edu/lessons/{lesson_id}/activities",
        headers=teacher,
        json={
            "activity_type": "reading",
            "title": "Read and annotate",
            "position": 1,
            "content_version_id": second.get_json()["version"]["id"],
            "student_payload": {"prompt": "Find evidence for the turning point."},
            "teacher_payload": {
                "answer_key": "The character decides to ask for help.",
                "rubric": {"evidence": 2},
            },
        },
    )
    assert activity.status_code == 201

    publication = client.post(
        f"/api/edu/lessons/{lesson_id}/publish",
        headers={**teacher, "Idempotency-Key": "publish-lesson-1"},
        json={},
    )
    assert publication.status_code == 201
    repeated = client.post(
        f"/api/edu/lessons/{lesson_id}/publish",
        headers={**teacher, "Idempotency-Key": "publish-lesson-1"},
        json={},
    )
    assert repeated.status_code == 200
    assert repeated.get_json()["id"] == publication.get_json()["id"]

    student_release = client.get(
        f"/api/edu/lessons/{lesson_id}/release",
        headers=student,
    )
    assert student_release.status_code == 200
    release_text = str(student_release.get_json())
    assert "Find evidence" in release_text
    assert "answer_key" not in release_text
    assert "ask for help" not in release_text

    teacher_release = client.get(
        f"/api/edu/lessons/{lesson_id}/publication",
        headers=teacher,
    )
    assert teacher_release.status_code == 200
    assert (
        teacher_release.get_json()["teacher_evaluation_manifest"]["activities"][0][
            "answer_key"
        ]
        == "The character decides to ask for help."
    )
    assert client.get(
        f"/api/edu/lessons/{lesson_id}/publication",
        headers=student,
    ).status_code == 404
    assert client.get(
        f"/api/edu/lessons/{lesson_id}/release",
        headers=outsider,
    ).status_code == 404
    structure = client.get(
        f"/api/edu/courses/{created_course['id']}/structure",
        headers=student,
    )
    assert structure.status_code == 200
    assert structure.get_json()["units"][0]["lessons"][0]["id"] == lesson_id
    assert client.get(
        f"/api/edu/courses/{created_course['id']}/structure",
        headers=outsider,
    ).status_code == 404


@pytest.mark.parametrize(
    ("subject_code", "grade_band", "genre"),
    [
        ("high_school_english", "senior_high", "narrative"),
        ("primary_chinese", "primary", "fairy_tale"),
    ],
)
def test_subject_templates_accept_supported_reading_writing_genres(
    app, subject_code, grade_band, genre
):
    client = app.test_client()
    teacher = headers(app, "teacher")
    created_course = course(client, teacher, subject_code, grade_band)

    response = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Integrated lesson",
            "learning_domain": "integrated",
            "theme_code": "growth",
            "text_genre_code": genre,
            "lesson_type_code": "reading_writing",
            "duration_minutes": 40,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["text_genre_code"] == genre


def test_lesson_template_rejects_cross_subject_genre_and_incomplete_plan(app):
    client = app.test_client()
    teacher = headers(app, "teacher")
    created_course = course(client, teacher, "primary_chinese", "primary")

    invalid_genre = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Invalid",
            "learning_domain": "reading",
            "theme_code": "nature",
            "text_genre_code": "argumentative",
            "lesson_type_code": "reading",
            "duration_minutes": 40,
        },
    )
    assert invalid_genre.status_code == 400

    valid_lesson = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "A fairy tale",
            "learning_domain": "integrated",
            "theme_code": "imagination",
            "text_genre_code": "fairy_tale",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 40,
        },
    ).get_json()
    invalid_plan = client.post(
        f"/api/edu/lessons/{valid_lesson['id']}/contents",
        headers=teacher,
        json={
            "kind": "lesson_plan",
            "schema_name": "lesson_plan_json",
            "source_json": {"objectives": [], "stages": []},
        },
    )
    assert invalid_plan.status_code == 400


def test_lesson_detail_and_content_history_are_membership_scoped(app):
    client = app.test_client()
    teacher = headers(app, "teacher")
    student = headers(app, "student")
    outsider = headers(app, "outsider")
    created_course = course(client, teacher)
    join(client, teacher, student, created_course["id"])
    lesson = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Draft narrative",
            "learning_domain": "integrated",
            "theme_code": "growth",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    content = client.post(
        f"/api/edu/lessons/{lesson['id']}/contents",
        headers=teacher,
        json={
            "kind": "lesson_plan",
            "schema_name": "lesson_plan_json",
            "source_json": lesson_plan(),
        },
    ).get_json()
    second = client.post(
        f"/api/edu/contents/{content['content']['id']}/versions",
        headers=teacher,
        json={
            "schema_name": "lesson_plan_json",
            "source_json": {
                **lesson_plan(),
                "objectives": [{"id": "v2", "description": "Revise the narrative"}],
            },
        },
    ).get_json()

    teacher_detail = client.get(
        f"/api/edu/lessons/{lesson['id']}", headers=teacher
    )
    assert teacher_detail.status_code == 200
    assert teacher_detail.get_json()["status"] == "draft"
    assert teacher_detail.get_json()["current_published_version_id"] is None
    assert client.get(
        f"/api/edu/lessons/{lesson['id']}", headers=student
    ).status_code == 404

    contents = client.get(
        f"/api/edu/lessons/{lesson['id']}/contents", headers=teacher
    )
    assert contents.status_code == 200
    assert contents.get_json()["items"][0]["current_version_id"] == second["version"]["id"]
    versions = client.get(
        f"/api/edu/contents/{content['content']['id']}/versions", headers=teacher
    )
    assert versions.status_code == 200
    assert [row["version_number"] for row in versions.get_json()["items"]] == [1, 2]
    assert versions.get_json()["items"][1]["source_json"]["objectives"][0]["id"] == "v2"

    assert client.get(
        f"/api/edu/lessons/{lesson['id']}/contents", headers=student
    ).status_code == 404
    assert client.get(
        f"/api/edu/contents/{content['content']['id']}/versions", headers=outsider
    ).status_code == 404


def test_teacher_exports_editable_json_and_html_with_pptx_fallback(app):
    client = app.test_client()
    teacher = headers(app, "export-teacher")
    outsider = headers(app, "export-outsider")
    created_course = course(client, teacher)
    lesson = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Exportable narrative lesson",
            "learning_domain": "integrated",
            "theme_code": "growth",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    content = client.post(
        f"/api/edu/lessons/{lesson['id']}/contents",
        headers=teacher,
        json={
            "kind": "lesson_plan",
            "schema_name": "lesson_plan_json",
            "source_json": lesson_plan(),
            "rendered_html": "<article><h1>Narrative lesson</h1></article>",
        },
    ).get_json()["content"]

    editable = client.get(
        f"/api/edu/contents/{content['id']}/export?format=json",
        headers=teacher,
    )
    assert editable.status_code == 200
    assert editable.mimetype == "application/json"
    assert "attachment;" in editable.headers["Content-Disposition"]
    assert editable.get_json()["source_json"]["subject_code"] == "high_school_english"

    html = client.get(
        f"/api/edu/contents/{content['id']}/export?format=html",
        headers=teacher,
    )
    assert html.status_code == 200
    assert html.mimetype == "text/html"
    assert b"Narrative lesson" in html.data

    unavailable_pptx = client.get(
        f"/api/edu/contents/{content['id']}/export?format=pptx",
        headers=teacher,
    )
    assert unavailable_pptx.status_code == 424
    assert unavailable_pptx.get_json()["fallback_formats"] == ["html", "json"]
    assert client.get(
        f"/api/edu/contents/{content['id']}/export?format=json",
        headers=outsider,
    ).status_code == 404
