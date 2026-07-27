from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class EducationCourseTestConfig:
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

    app = create_edu_app(EducationCourseTestConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_course(client, headers, title="English Reading Lab"):
    return client.post(
        "/api/edu/courses",
        headers=headers,
        json={
            "title": title,
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": "Reading and writing",
        },
    )


def test_teacher_creates_course_and_is_the_active_teacher_member(education_app):
    client = education_app.test_client()
    teacher = auth_headers(education_app, "teacher-1")

    response = create_course(client, teacher)

    assert response.status_code == 201
    course = response.get_json()
    assert course["owner_user_id"] == "teacher-1"
    assert course["membership_role"] == "teacher"
    assert course["subject_code"] == "high_school_english"

    listed = client.get("/api/edu/courses", headers=teacher)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.get_json()["items"]] == [course["id"]]


def test_invitation_joins_two_students_idempotently_and_hides_token_hash(education_app):
    client = education_app.test_client()
    teacher = auth_headers(education_app, "teacher-1")
    student_a = auth_headers(education_app, "student-a")
    student_b = auth_headers(education_app, "student-b")
    course = create_course(client, teacher).get_json()

    invitation_response = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers=teacher,
        json={"max_uses": 2, "expires_in_hours": 24},
    )
    assert invitation_response.status_code == 201
    invitation = invitation_response.get_json()
    assert invitation["token"]
    assert "token_hash" not in invitation

    first_join = client.post(
        "/api/edu/invitations/accept",
        headers=student_a,
        json={"token": invitation["token"]},
    )
    repeated_join = client.post(
        "/api/edu/invitations/accept",
        headers=student_a,
        json={"token": invitation["token"]},
    )
    second_join = client.post(
        "/api/edu/invitations/accept",
        headers=student_b,
        json={"token": invitation["token"]},
    )

    assert first_join.status_code == 200
    assert repeated_join.status_code == 200
    assert repeated_join.get_json()["membership"]["id"] == first_join.get_json()["membership"]["id"]
    assert second_join.status_code == 200

    members = client.get(
        f"/api/edu/courses/{course['id']}/members",
        headers=teacher,
    )
    assert members.status_code == 200
    assert {(item["user_id"], item["role"]) for item in members.get_json()["items"]} == {
        ("teacher-1", "teacher"),
        ("student-a", "student"),
        ("student-b", "student"),
    }


def test_course_authorization_uses_membership_not_client_sub_role(education_app):
    client = education_app.test_client()
    teacher = auth_headers(education_app, "teacher-1")
    outsider = auth_headers(education_app, "outsider")
    course = create_course(client, teacher).get_json()

    denied_members = client.get(
        f"/api/edu/courses/{course['id']}/members",
        headers={**outsider, "X-Workspace-Sub-Role": "teacher"},
    )
    denied_invite = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers={**outsider, "X-Workspace-Sub-Role": "teacher"},
        json={},
    )

    assert denied_members.status_code == 404
    assert denied_invite.status_code == 404


def test_course_detail_is_scoped_and_returns_server_membership_role(education_app):
    client = education_app.test_client()
    teacher = auth_headers(education_app, "teacher-1")
    outsider = auth_headers(education_app, "outsider")
    course = create_course(client, teacher).get_json()

    allowed = client.get(f"/api/edu/courses/{course['id']}", headers=teacher)
    denied = client.get(f"/api/edu/courses/{course['id']}", headers=outsider)

    assert allowed.status_code == 200
    assert allowed.get_json()["membership_role"] == "teacher"
    assert denied.status_code == 404


def test_revoked_and_expired_or_exhausted_invitations_are_rejected(education_app):
    client = education_app.test_client()
    teacher = auth_headers(education_app, "teacher-1")
    student_a = auth_headers(education_app, "student-a")
    student_b = auth_headers(education_app, "student-b")
    course = create_course(client, teacher).get_json()

    invitation = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers=teacher,
        json={"max_uses": 1, "expires_in_hours": 1},
    ).get_json()

    assert client.post(
        "/api/edu/invitations/accept",
        headers=student_a,
        json={"token": invitation["token"]},
    ).status_code == 200
    assert client.post(
        "/api/edu/invitations/accept",
        headers=student_b,
        json={"token": invitation["token"]},
    ).status_code == 410

    revocable = client.post(
        f"/api/edu/courses/{course['id']}/invitations",
        headers=teacher,
        json={"max_uses": 2},
    ).get_json()
    revoked = client.delete(
        f"/api/edu/courses/{course['id']}/invitations/{revocable['id']}",
        headers=teacher,
    )
    assert revoked.status_code == 200
    assert client.post(
        "/api/edu/invitations/accept",
        headers=student_b,
        json={"token": revocable["token"]},
    ).status_code == 410
