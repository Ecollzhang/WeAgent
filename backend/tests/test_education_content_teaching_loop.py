from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class Config:
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
def setup():
    from services.edu.app import create_edu_app
    from services.edu.content_routes import education_content_api

    app = create_edu_app(Config)
    if education_content_api.name not in app.blueprints:
        app.register_blueprint(education_content_api, url_prefix="/api/edu")
    with app.app_context():
        db.create_all()
    client = app.test_client()

    def auth(user_id):
        with app.app_context():
            token = create_access_token(identity=user_id)
        return {"Authorization": f"Bearer {token}"}

    teacher = auth("teacher")
    student_a = auth("student-a")
    student_b = auth("student-b")
    outsider = auth("outsider")
    created_course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Primary Chinese",
            "subject_code": "primary_chinese",
            "grade_band": "primary",
        },
    ).get_json()
    for student in (student_a, student_b):
        invitation = client.post(
            f"/api/edu/courses/{created_course['id']}/invitations",
            headers=teacher,
            json={},
        ).get_json()
        assert client.post(
            "/api/edu/invitations/accept",
            headers=student,
            json={"token": invitation["token"]},
        ).status_code == 200
    lesson = client.post(
        f"/api/edu/courses/{created_course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Retell a fable",
            "learning_domain": "integrated",
            "theme_code": "wisdom",
            "text_genre_code": "fable",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 40,
        },
    ).get_json()
    yield app, client, teacher, student_a, student_b, outsider, created_course, lesson
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_teacher_publishes_writing_assignment_two_students_submit_and_receive_feedback(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    created = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Retell from another point of view",
            "kind": "writing",
            "instruction_json": {
                "prompt": "Retell the fable in 200 words.",
                "student_rubric": ["clear sequence", "character voice"],
            },
            "evaluation_json": {
                "answer_notes": "Accept different viewpoints.",
                "rubric": {"sequence": 5, "voice": 5},
            },
            "max_attempts": 2,
        },
    )
    assert created.status_code == 201
    assignment = created.get_json()
    assert "evaluation_json" not in assignment

    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/publish",
        headers=teacher,
    ).status_code == 200
    student_listing = client.get(
        f"/api/edu/courses/{course['id']}/assignments",
        headers=student_a,
    )
    assert student_listing.status_code == 200
    assert "answer_notes" not in str(student_listing.get_json())

    submission_a = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={"answer_json": {"writing": "Once, the fox told the story differently."}},
    )
    submission_b = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_b,
        json={"answer_json": {"writing": "The crow remembered the lesson."}},
    )
    assert submission_a.status_code == 201
    assert submission_b.status_code == 201
    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=outsider,
        json={"answer_json": {"writing": "not enrolled"}},
    ).status_code == 404

    revised = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={
            "answer_json": {"writing": "Once, the fox told a clearer story."},
            "source_version_id": submission_a.get_json()["version"]["id"],
        },
    )
    assert revised.status_code == 201
    assert revised.get_json()["version"]["version_number"] == 2
    assert revised.get_json()["submission"]["attempt_count"] == 2
    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={"answer_json": {"writing": "third attempt"}},
    ).status_code == 409

    feedback = client.post(
        f"/api/edu/submissions/{revised.get_json()['submission']['id']}/feedback",
        headers=teacher,
        json={
            "feedback_json": {
                "strengths": ["Clearer sequence"],
                "next_steps": ["Add sensory detail"],
            },
            "score": 8,
        },
    )
    assert feedback.status_code == 201
    own_feedback = client.get(
        f"/api/edu/submissions/{revised.get_json()['submission']['id']}/feedback",
        headers=student_a,
    )
    assert own_feedback.status_code == 200
    assert own_feedback.get_json()["items"][0]["score"] == 8
    assert client.get(
        f"/api/edu/submissions/{revised.get_json()['submission']['id']}/feedback",
        headers=student_b,
    ).status_code == 404


def test_teacher_analytics_reports_completion_scores_and_learning_events(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Reading check",
            "kind": "quiz",
            "instruction_json": {"items": [{"stem": "What is the lesson?"}]},
            "evaluation_json": {"answer_key": ["Think before acting"]},
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    submitted = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={"answer_json": {"item_1": "Think before acting"}},
    ).get_json()
    client.post(
        f"/api/edu/submissions/{submitted['submission']['id']}/feedback",
        headers=teacher,
        json={"feedback_json": {"comment": "Correct"}, "score": 10},
    )

    analytics = client.get(
        f"/api/edu/courses/{course['id']}/analytics",
        headers=teacher,
    )
    assert analytics.status_code == 200
    report = analytics.get_json()
    assert report["active_students"] == 2
    assert report["published_assignments"] == 1
    assert report["submitted_students"] == 1
    assert report["completion_rate"] == 0.5
    assert report["average_score"] == 10.0
    assert report["learning_domain_counts"] == {"integrated": 1}
    assert report["assignment_kind_counts"] == {"quiz": 1}
    assert report["event_counts"]["AssignmentSubmitted"] == 1
    assert report["event_counts"]["FeedbackReleased"] == 1
    assert client.get(
        f"/api/edu/courses/{course['id']}/analytics",
        headers=student_a,
    ).status_code == 404
