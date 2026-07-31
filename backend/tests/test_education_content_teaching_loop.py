from datetime import timedelta
from io import BytesIO

import pytest
from flask_jwt_extended import create_access_token
from reportlab.pdfgen import canvas

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


def test_assignment_detail_hides_evaluation_from_students(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Private answer contract",
            "kind": "quiz",
            "instruction_json": {"items": [{"stem": "What did the character learn?"}]},
            "evaluation_json": {"answer_key": ["Be honest"]},
        },
    ).get_json()

    teacher_detail = client.get(
        f"/api/edu/assignments/{assignment['id']}", headers=teacher
    )
    assert teacher_detail.status_code == 200
    assert teacher_detail.get_json()["evaluation_json"]["answer_key"] == ["Be honest"]
    assert client.get(
        f"/api/edu/assignments/{assignment['id']}", headers=student_a
    ).status_code == 404

    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    student_detail = client.get(
        f"/api/edu/assignments/{assignment['id']}", headers=student_a
    )
    assert student_detail.status_code == 200
    assert "evaluation_json" not in student_detail.get_json()
    assert "answer_key" not in str(student_detail.get_json())
    assert client.get(
        f"/api/edu/assignments/{assignment['id']}", headers=outsider
    ).status_code == 404


def test_student_draft_survives_refresh_and_submit_freezes_visible_version(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Writing draft",
            "kind": "writing",
            "instruction_json": {"prompt": "Retell the ending."},
            "evaluation_json": {"rubric": {"clarity": 10}},
            "max_attempts": 2,
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)

    saved = client.put(
        f"/api/edu/assignments/{assignment['id']}/submission/draft",
        headers=student_a,
        json={"answer_json": {"writing": "First saved draft."}},
    )
    assert saved.status_code == 200
    restored = client.get(
        f"/api/edu/assignments/{assignment['id']}/submission",
        headers=student_a,
    )
    assert restored.status_code == 200
    assert restored.get_json()["draft"]["answer_json"]["writing"] == "First saved draft."
    assert restored.get_json()["versions"] == []

    submitted = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={},
    )
    assert submitted.status_code == 201
    frozen = submitted.get_json()["version"]
    assert frozen["answer_json"]["writing"] == "First saved draft."
    after_submit = client.get(
        f"/api/edu/assignments/{assignment['id']}/submission",
        headers=student_a,
    ).get_json()
    assert after_submit["draft"] is None
    assert after_submit["versions"][0]["id"] == frozen["id"]
    assert after_submit["versions"][0]["answer_json"]["writing"] == "First saved draft."

    client.put(
        f"/api/edu/assignments/{assignment['id']}/submission/draft",
        headers=student_a,
        json={"answer_json": {"writing": "Revised saved draft."}},
    )
    revised = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={},
    )
    assert revised.status_code == 201
    assert revised.get_json()["version"]["version_number"] == 2
    assert revised.get_json()["version"]["source_version_id"] == frozen["id"]
    history = client.get(
        f"/api/edu/assignments/{assignment['id']}/submission",
        headers=student_a,
    ).get_json()["versions"]
    assert history[0]["answer_json"]["writing"] == "First saved draft."
    assert history[1]["answer_json"]["writing"] == "Revised saved draft."

    assert client.get(
        f"/api/edu/assignments/{assignment['id']}/submission",
        headers=student_b,
    ).get_json()["submission"] is None
    assert client.get(
        f"/api/edu/assignments/{assignment['id']}/submission",
        headers=outsider,
    ).status_code == 404


def test_teacher_reads_submission_bodies_only_inside_assignment_course(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Reading response",
            "kind": "mixed",
            "instruction_json": {"prompt": "Respond with evidence."},
            "evaluation_json": {"answer_notes": "Look for evidence."},
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={"answer_json": {"response": "The final paragraph is evidence."}},
    )

    reviewed = client.get(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=teacher,
    )
    assert reviewed.status_code == 200
    assert reviewed.get_json()["items"][0]["student_user_id"] == "student-a"
    assert (
        reviewed.get_json()["items"][0]["versions"][0]["answer_json"]["response"]
        == "The final paragraph is evidence."
    )
    student_view = client.get(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
    )
    assert student_view.get_json()["items"][0]["versions"][0]["answer_json"]
    assert client.get(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=outsider,
    ).status_code == 404


def test_teacher_imports_pdf_as_editable_assignment_and_publishes_source_file(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    pdf.drawString(72, 760, "Read the fable and explain the lesson with evidence.")
    pdf.save()
    pdf_bytes = pdf_buffer.getvalue()

    uploaded = client.post(
        f"/api/edu/courses/{course['id']}/assignment-imports",
        headers=teacher,
        data={
            "lesson_id": lesson["id"],
            "mode": "editable",
            "file": (BytesIO(pdf_bytes), "fable-work.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    import_job = uploaded.get_json()
    assert import_job["status"] == "uploaded"
    assert import_job["source_asset"]["original_filename"] == "fable-work.pdf"

    processed = client.post(
        f"/api/edu/assignment-imports/{import_job['id']}/process",
        headers=teacher,
    )
    assert processed.status_code == 200
    import_job = processed.get_json()
    assert import_job["status"] == "review_required"
    assert import_job["extractor_code"] == "pdf_text"
    assert "explain the lesson" in import_job["extracted_text"]
    assert import_job["draft_json"]["instruction_json"]["text"]

    created = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Fable evidence worksheet",
            "kind": "mixed",
            "instruction_json": import_job["draft_json"]["instruction_json"],
            "evaluation_json": {},
            "source_asset_ids": [import_job["source_asset"]["id"]],
        },
    )
    assert created.status_code == 201
    assignment = created.get_json()
    assert assignment["source_assets"][0]["original_filename"] == "fable-work.pdf"

    asset_id = import_job["source_asset"]["id"]
    assert client.get(
        f"/api/edu/assets/{asset_id}/download",
        headers=student_a,
    ).status_code == 404
    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/publish",
        headers=teacher,
    ).status_code == 200
    downloaded = client.get(
        f"/api/edu/assets/{asset_id}/download",
        headers=student_a,
    )
    assert downloaded.status_code == 200
    assert downloaded.data == pdf_bytes


def test_teacher_uses_assignment_overview_and_persisted_review_draft(setup):
    app, client, teacher, student_a, student_b, outsider, course, lesson = setup
    client.put(
        f"/api/edu/courses/{course['id']}/me/profile",
        headers=student_a,
        json={"display_name": "林同学"},
    )
    client.put(
        f"/api/edu/courses/{course['id']}/me/profile",
        headers=student_b,
        json={"display_name": "周同学"},
    )
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Fable evidence response",
            "kind": "writing",
            "instruction_json": {"text": "Explain the lesson with two details."},
            "evaluation_json": {
                "rubric": {"content": 6, "language": 4},
                "answer_notes": "Accept evidence-based interpretations.",
            },
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    submitted = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student_a,
        json={
            "answer_json": {
                "writing": "The character learns to listen. The final choice proves it."
            }
        },
    ).get_json()

    overview = client.get(
        f"/api/edu/assignments/{assignment['id']}/overview",
        headers=teacher,
    )
    assert overview.status_code == 200
    body = overview.get_json()
    assert body["metrics"]["expected"] == 2
    assert body["metrics"]["submitted"] == 1
    assert body["metrics"]["unsubmitted"] == 1
    assert body["metrics"]["pending_review"] == 1
    assert [row["display_name"] for row in body["students"]] == ["林同学", "周同学"]
    assert body["students"][0]["submission_id"] == submitted["submission"]["id"]
    assert body["students"][1]["submission_id"] is None

    review = client.get(
        f"/api/edu/submissions/{submitted['submission']['id']}/review",
        headers=teacher,
    )
    assert review.status_code == 200
    review_body = review.get_json()
    assert review_body["student"]["display_name"] == "林同学"
    assert review_body["evidence"]["kind"] == "text"
    assert "final choice" in review_body["evidence"]["text"]
    assert review_body["rubric"][0]["max_score"] == 6
    assert review_body["review_draft"] is None
    assert review_body["analysis_state"] == "missing"

    saved = client.put(
        f"/api/edu/submissions/{submitted['submission']['id']}/review-draft",
        headers=teacher,
        json={
            "rubric_scores": {"content": 5, "language": 3},
            "feedback_json": {
                "strengths": ["Uses relevant evidence"],
                "issues": ["Explain how the detail proves the lesson"],
                "next_steps": ["Add one reasoning sentence"],
                "comment": "Clear response with a useful next step.",
            },
            "annotations": [
                {"quote": "final choice", "comment": "Strong evidence anchor"}
            ],
            "revision_requested": False,
        },
    )
    assert saved.status_code == 200
    assert saved.get_json()["score"] == 8

    restored = client.get(
        f"/api/edu/submissions/{submitted['submission']['id']}/review",
        headers=teacher,
    ).get_json()
    assert restored["review_draft"]["rubric_scores"]["content"] == 5
    assert restored["submission"]["status"] == "reviewing"

    released = client.post(
        f"/api/edu/submissions/{submitted['submission']['id']}/review/publish",
        headers=teacher,
        json={},
    )
    assert released.status_code == 201
    assert released.get_json()["score"] == 8
    assert released.get_json()["version_number"] == 1

    completed = client.get(
        f"/api/edu/assignments/{assignment['id']}/overview",
        headers=teacher,
    ).get_json()
    assert completed["metrics"]["pending_review"] == 0
    assert completed["metrics"]["graded"] == 1
    assert completed["metrics"]["average_score"] == 8
