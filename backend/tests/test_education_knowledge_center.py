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


def test_published_question_pointer_hides_new_teacher_draft_and_supports_true_false(app):
    client = app.test_client()
    teacher, student, course = course_with_student(client, app)
    created = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json={
            "title": "Text evidence check",
            "question_type": "true_false",
            "prompt": "Della sells her hair before buying Jim's gift.",
            "difficulty": "easy",
            "score": 2,
            "knowledge_points": ["sequence of events"],
            "correct_answer": True,
            "explanation": "The action happens before she buys the chain.",
        },
    )
    assert created.status_code == 201
    item = created.get_json()
    assert client.post(
        f"/api/edu/questions/{item['id']}/publish", headers=teacher
    ).status_code == 200

    edited = client.post(
        f"/api/edu/questions/{item['id']}/versions",
        headers=teacher,
        json={
            "title": "Text evidence check",
            "question_type": "true_false",
            "prompt": "Teacher draft that must remain private.",
            "difficulty": "medium",
            "score": 2,
            "knowledge_points": ["sequence of events"],
            "correct_answer": False,
            "explanation": "Draft explanation.",
        },
    ).get_json()
    assert edited["current_version"]["version_number"] == 2
    assert edited["published_version_id"] != edited["current_version_id"]

    student_item = client.get(
        f"/api/edu/courses/{course['id']}/questions", headers=student
    ).get_json()["items"][0]
    assert student_item["current_version"]["prompt"] == (
        "Della sells her hair before buying Jim's gift."
    )
    assert "answer" not in student_item["current_version"]


def test_reading_stimulus_groups_questions_and_paper_preview_is_hydrated(app):
    client = app.test_client()
    teacher, student, course = course_with_student(client, app)
    stimulus_response = client.post(
        f"/api/edu/courses/{course['id']}/stimuli",
        headers=teacher,
        json={
            "title": "The Gift of the Magi — classroom excerpt",
            "stimulus_type": "reading_passage",
            "language": "en",
            "content": {
                "paragraphs": [
                    "Della counted the money again. There was only one dollar and eighty-seven cents.",
                    "She had been saving every penny she could for Jim's present.",
                ]
            },
            "source_refs": [
                {
                    "title": "The Gift of the Magi",
                    "author": "O. Henry",
                    "url": "https://www.gutenberg.org/ebooks/7256",
                    "rights": "Public domain in the USA",
                }
            ],
        },
    )
    assert stimulus_response.status_code == 201
    stimulus = stimulus_response.get_json()
    assert stimulus["current_version"]["word_or_character_count"] > 10
    assert client.post(
        f"/api/edu/stimuli/{stimulus['id']}/publish", headers=teacher
    ).status_code == 200

    question_ids = []
    for order, payload in enumerate(
        [
            {
                **question_payload(),
                "title": "Inference from detail",
                "prompt": "What does Della's repeated counting reveal?",
            },
            {
                "title": "Evidence response",
                "question_type": "short_answer",
                "prompt": "Use one detail to explain Della's situation.",
                "difficulty": "medium",
                "score": 5,
                "knowledge_points": ["text evidence"],
                "correct_answer": "She has very little money but has saved carefully for Jim.",
                "rubric": {"evidence": 3, "explanation": 2},
                "explanation": "Responses must connect a quoted detail to the inference.",
            },
        ],
        start=1,
    ):
        response = client.post(
            f"/api/edu/courses/{course['id']}/questions",
            headers=teacher,
            json={
                **payload,
                "stimulus_version_id": stimulus["current_version_id"],
                "stimulus_order": order,
            },
        )
        assert response.status_code == 201
        item = response.get_json()
        question_ids.append(item["id"])
        client.post(f"/api/edu/questions/{item['id']}/publish", headers=teacher)

    grouped = client.get(
        f"/api/edu/courses/{course['id']}/questions", headers=teacher
    ).get_json()
    assert grouped["stimuli"][0]["question_count"] == 2
    assert [row["current_version"]["stimulus_order"] for row in grouped["stimuli"][0]["questions"]] == [1, 2]

    revised_stimulus = client.post(
        f"/api/edu/stimuli/{stimulus['id']}/versions",
        headers=teacher,
        json={
            "content": {
                "paragraphs": [
                    "Della counted the money three times. There was only one dollar and eighty-seven cents.",
                    "She had been saving every penny she could for Jim's present.",
                ]
            },
            "source_refs": stimulus["current_version"]["source_refs"],
            "language": "en",
        },
    )
    assert revised_stimulus.status_code == 201
    regrouped = client.get(
        f"/api/edu/courses/{course['id']}/questions", headers=teacher
    ).get_json()
    assert regrouped["stimuli"][0]["question_count"] == 2

    paper = client.post(
        f"/api/edu/courses/{course['id']}/papers/compose",
        headers=teacher,
        json={
            "title": "Authentic reading check",
            "purpose": "practice",
            "duration_minutes": 25,
            "item_ids": question_ids,
        },
    ).get_json()
    teacher_student_preview = client.get(
        f"/api/edu/papers/{paper['id']}/preview?mode=student", headers=teacher
    )
    assert teacher_student_preview.status_code == 200
    assert all(
        "answer" not in row
        for row in teacher_student_preview.get_json()["questions"]
    )
    client.post(f"/api/edu/papers/{paper['id']}/publish", headers=teacher)
    student_preview = client.get(
        f"/api/edu/papers/{paper['id']}/preview?mode=student", headers=student
    )
    assert student_preview.status_code == 200
    preview = student_preview.get_json()
    assert len(preview["stimuli"]) == 1
    assert len(preview["questions"]) == 2
    assert all("answer" not in row for row in preview["questions"])
    teacher_preview = client.get(
        f"/api/edu/papers/{paper['id']}/preview?mode=teacher", headers=teacher
    ).get_json()
    assert all("answer" in row for row in teacher_preview["questions"])

    revised = client.post(
        f"/api/edu/papers/{paper['id']}/versions",
        headers=teacher,
        json={"title": "Authentic reading check — revised", "duration_minutes": 30, "item_ids": question_ids},
    )
    assert revised.status_code == 201
    revised_payload = revised.get_json()
    assert revised_payload["current_version"]["version_number"] == 2
    assert revised_payload["published_version_id"] != revised_payload["current_version_id"]


def test_question_bank_can_be_organized_by_course_lesson(app):
    client = app.test_client()
    teacher, _, course = course_with_student(client, app)
    first_lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Reading the opening",
            "learning_domain": "reading",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    second_lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Explaining the irony",
            "learning_domain": "writing",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()

    stimulus = client.post(
        f"/api/edu/courses/{course['id']}/stimuli",
        headers=teacher,
        json={
            "title": "The Gift of the Magi — opening",
            "lesson_id": first_lesson["id"],
            "stimulus_type": "reading_passage",
            "language": "en",
            "content": {"paragraphs": ["One dollar and eighty-seven cents. That was all."]},
            "source_refs": [],
        },
    )
    assert stimulus.status_code == 201
    assert stimulus.get_json()["lesson_id"] == first_lesson["id"]

    grouped_question = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json={
            **question_payload(),
            "stimulus_version_id": stimulus.get_json()["current_version_id"],
            "stimulus_order": 1,
        },
    )
    assert grouped_question.status_code == 201
    assert grouped_question.get_json()["lesson_id"] == first_lesson["id"]

    standalone = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json={**question_payload(), "title": "Irony transfer", "lesson_id": second_lesson["id"]},
    )
    assert standalone.status_code == 201
    assert standalone.get_json()["lesson_id"] == second_lesson["id"]

    listed = client.get(
        f"/api/edu/courses/{course['id']}/questions", headers=teacher
    ).get_json()
    assert {row["lesson_id"] for row in listed["items"]} == {
        first_lesson["id"],
        second_lesson["id"],
    }


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
