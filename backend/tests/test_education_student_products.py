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


def test_weakness_includes_released_assignment_feedback_evidence(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Narrative turning points",
            "learning_domain": "integrated",
            "theme_code": "school_life",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Explain the turning point",
            "kind": "writing",
            "instruction_json": {"prompt": "Use two details from the passage."},
            "evaluation_json": {"rubric": {"evidence": 10}},
            "max_score": 10,
        },
    ).get_json()
    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/publish",
        headers=teacher,
    ).status_code == 200
    submission = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student,
        json={"answer_json": {"writing": "The character changed after the letter."}},
    ).get_json()["submission"]
    assert client.post(
        f"/api/edu/submissions/{submission['id']}/feedback",
        headers=teacher,
        json={
            "feedback_json": {
                "strengths": ["The turning point is identified."],
                "weaknesses": ["Textual evidence is not explained."],
                "next_steps": ["Connect each quotation to the character change."],
            },
            "score": 7,
        },
    ).status_code == 201

    response = client.post(
        f"/api/edu/courses/{course['id']}/weakness-analysis",
        headers=student,
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["data_state"] == "ready"
    assert {
        row["knowledge_point"] for row in payload["weaknesses"]
    } == {
        "Textual evidence is not explained.",
        "Connect each quotation to the character change.",
    }
    assert all(
        row["source_type"] == "assignment_feedback"
        for row in payload["evidence"]
    )
    assert all(
        row["submission_id"] == submission["id"]
        for row in payload["evidence"]
    )


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


def test_teacher_insight_aggregates_only_confirmed_assignment_scores(app):
    client = app.test_client()
    teacher, student_a, course = setup_course(client, app)
    student_b = auth(app, "student-b")
    student_pending = auth(app, "student-pending")
    for student in (student_b, student_pending):
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
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Narrative evidence writing",
            "learning_domain": "writing",
            "theme_code": "growth",
            "text_genre_code": "narrative",
            "lesson_type_code": "writing",
            "duration_minutes": 45,
        },
    ).get_json()
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Write from evidence",
            "kind": "writing",
            "max_score": 20,
            "instruction_json": {"prompt": "Write a short narrative."},
            "evaluation_json": {"rubric": {"evidence": 10, "voice": 10}},
        },
    ).get_json()
    assert assignment["max_score"] == 20
    assert client.post(
        f"/api/edu/assignments/{assignment['id']}/publish",
        headers=teacher,
    ).status_code == 200

    submissions = []
    for index, student in enumerate((student_a, student_b, student_pending), 1):
        response = client.post(
            f"/api/edu/assignments/{assignment['id']}/submissions",
            headers=student,
            json={"answer_json": {"writing": f"Draft {index}"}},
        )
        assert response.status_code == 201
        submissions.append(response.get_json()["submission"])
    for submission, score in zip(submissions[:2], (16, 12)):
        assert client.post(
            f"/api/edu/submissions/{submission['id']}/feedback",
            headers=teacher,
            json={"feedback_json": {"confirmed": True}, "score": score},
        ).status_code == 201

    refreshed = client.post(
        f"/api/edu/courses/{course['id']}/student-insights/refresh",
        headers=teacher,
    )

    assert refreshed.status_code == 201
    payload = refreshed.get_json()
    overview = payload["class_overview"]
    assert overview["student_count"] == 3
    assert overview["graded_student_count"] == 2
    assert overview["pending_review_count"] == 1
    assert overview["completion_rate"] == 1.0
    assert overview["highest_score"] == 80.0
    assert overview["lowest_score"] == 60.0
    assert overview["average_score"] == 70.0
    assert overview["median_score"] == 70.0
    assert sum(bucket["count"] for bucket in overview["score_distribution"]) == 2
    assert overview["trend"][0]["assessment_id"] == assignment["id"]

    rows = {row["student_user_id"]: row for row in payload["items"]}
    assert rows["student"]["summary"]["official_average_score"] == 80.0
    assert rows["student-b"]["summary"]["official_average_score"] == 60.0
    assert rows["student-pending"]["summary"]["official_average_score"] is None
    assert rows["student-pending"]["summary"]["pending_review_count"] == 1
    assert rows["student-pending"]["data_state"] == "pending_review"
    assert all(
        evidence["score_status"] == "teacher_confirmed"
        for row in rows.values()
        for evidence in row["evidence"]
        if evidence["object_type"] == "assignment_submission"
        and evidence.get("score") is not None
    )

    listed = client.get(
        f"/api/edu/courses/{course['id']}/student-insights",
        headers=teacher,
    ).get_json()
    assert listed["class_overview"]["average_score"] == 70.0
    assert client.get(
        f"/api/edu/courses/{course['id']}/student-insights",
        headers=student_a,
    ).status_code == 404
