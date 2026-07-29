from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class ProductAgentRunTestConfig:
    TESTING = True
    SERVICE_NAME = "weagent-edu-product-agent-test"
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

    app = create_edu_app(ProductAgentRunTestConfig)
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


def seed_course(app):
    client = app.test_client()
    teacher = auth_headers(app, "teacher")
    student = auth_headers(app, "student")
    other_student = auth_headers(app, "other-student")
    course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "高中英语阅读与写作",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
        },
    ).get_json()
    for member_headers in (student, other_student):
        invitation = client.post(
            f"/api/edu/courses/{course['id']}/invitations",
            headers=teacher,
            json={},
        ).get_json()
        accepted = client.post(
            "/api/edu/invitations/accept",
            headers=member_headers,
            json={"token": invitation["token"]},
        )
        assert accepted.status_code == 200
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "校园生活叙事阅读",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    return course, lesson, teacher, student, other_student


class FakeProductRuntime:
    def __init__(self):
        self.started = []
        self.snapshot = {"status": "running", "agent_runs": []}

    def start_workflow(
        self,
        *,
        authorization,
        title,
        prompt,
        agent_ids,
        workflow,
        education_run_grant=None,
    ):
        index = len(self.started) + 1
        self.started.append(
            {
                "authorization": authorization,
                "title": title,
                "prompt": prompt,
                "agent_ids": agent_ids,
                "workflow": workflow,
                "education_run_grant": education_run_grant,
            }
        )
        return {
            "conversation_id": f"product-conversation-{index}",
            "sandbox_session_id": f"product-sandbox-{index}",
            "message_id": f"product-message-{index}",
        }

    def get_snapshot(self, *, authorization, conversation_id):
        return self.snapshot


def test_student_starts_scoped_mock_exam_agent_run(education_app):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, teacher, student, _ = seed_course(education_app)

    response = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "mock_exam",
            "options": {
                "title": "校园生活专项诊断",
                "question_count": 6,
                "duration_minutes": 35,
            },
        },
    )
    forbidden = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "mock_exam",
            "options": {},
        },
    )

    assert response.status_code == 202
    assert forbidden.status_code == 403
    run = response.get_json()
    assert run["status"] == "running"
    assert run["workflow_code"] == "product.mock_exam"
    assert run["input_payload"]["options"]["question_count"] == 6
    assert [node["agent_role"] for node in run["nodes"]] == [
        "learning_planner",
        "practice_coach",
    ]
    started = runtime.started[0]
    assert started["agent_ids"] == ["_edu_5", "_edu_6"]
    assert "edu.question_bank.search" in started["prompt"]
    assert "edu.mock_exam.create" in started["prompt"]
    assert "question_count=6" in started["prompt"]
    assert "不得传 course_id" in started["prompt"]
    assert len(started["education_run_grant"]) >= 40
    assert started["education_run_grant"] not in started["prompt"]


def test_teacher_courseware_product_requires_lesson_and_uses_draft_tools(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, student, _ = seed_course(education_app)

    missing_lesson = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "courseware",
        },
    )
    forbidden = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "lesson_id": lesson["id"],
            "product_code": "courseware",
        },
    )
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "lesson_id": lesson["id"],
            "product_code": "courseware",
            "options": {"requirements": "突出故事弧和读写迁移"},
        },
    )

    assert missing_lesson.status_code == 400
    assert forbidden.status_code == 403
    assert created.status_code == 202
    run = created.get_json()
    assert run["lesson_id"] == lesson["id"]
    assert [node["agent_role"] for node in run["nodes"]] == [
        "course_designer",
        "courseware_maker",
        "teaching_reviewer",
    ]
    started = runtime.started[0]
    assert started["agent_ids"] == ["_edu_1", "_edu_2", "_edu_9"]
    assert "edu.courseware.create" in started["prompt"]
    assert "slide_document" in started["prompt"]
    assert '"name":"education_action"' in started["prompt"]
    assert '"args":{"action":"edu.courseware.create","arguments":{' in (
        started["prompt"]
    )
    assert "Action-specific fields MUST be nested under args.arguments" in (
        started["prompt"]
    )
    assert "lesson_id is injected from the lesson-scoped Agent run" in (
        started["prompt"]
    )
    assert lesson["id"] not in started["prompt"]
    assert "不得自动发布" in started["prompt"]


def test_teacher_starts_agent_roster_import_with_structured_member_rows(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, teacher, student, _ = seed_course(education_app)
    members = [
        {"user_id": "student-three", "display_name": "林同学"},
        {"user_id": "student-four", "display_name": "周同学"},
    ]

    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "roster_import",
            "options": {"members": members},
        },
    )
    forbidden = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "roster_import",
            "options": {"members": members},
        },
    )
    invalid = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "roster_import",
            "options": {"members": []},
        },
    )

    assert created.status_code == 202
    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    run = created.get_json()
    assert [node["agent_role"] for node in run["nodes"]] == [
        "course_designer",
        "teaching_reviewer",
    ]
    started = runtime.started[0]
    assert "edu.course.members.list" in started["prompt"]
    assert "edu.course.members.import" in started["prompt"]
    assert "student-three" in started["prompt"]
    assert "林同学" in started["prompt"]

    imported = client.post(
        "/api/edu/tools/edu.course.members.import/invoke",
        headers={
            "X-Education-Run-Grant": started["education_run_grant"],
        },
        json={
            "agent_id": "_edu_1",
            "idempotency_key": "product-roster-import-v1",
            "arguments": {"members": members},
        },
    )
    roster = client.get(
        f"/api/edu/courses/{course['id']}/members",
        headers=teacher,
    ).get_json()["items"]

    assert imported.status_code == 200
    assert {"student-three", "student-four"} <= {
        member["user_id"] for member in roster
    }


def test_product_run_is_private_to_requesting_member(education_app):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, teacher, student, other_student = seed_course(education_app)
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "weakness_analysis",
            "options": {},
        },
    ).get_json()

    owner_view = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=student,
    )
    peer_view = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=other_student,
    )
    teacher_view = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=teacher,
    )
    owner_list = client.get(
        f"/api/edu/courses/{course['id']}/product-agent-runs",
        headers=student,
    )

    assert owner_view.status_code == 200
    assert peer_view.status_code == 404
    assert teacher_view.status_code == 404
    assert [row["id"] for row in owner_list.get_json()["items"]] == [created["id"]]


def test_student_agent_tool_write_is_visible_on_product_run(education_app):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, _, student, _ = seed_course(education_app)
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "course_mind_map",
            "options": {"title": "我的课程脉络"},
        },
    ).get_json()
    raw_grant = runtime.started[0]["education_run_grant"]

    tool_response = client.post(
        "/api/edu/tools/edu.mind_map.create/invoke",
        headers={"X-Education-Run-Grant": raw_grant},
        json={
            "agent_id": "_edu_7",
            "idempotency_key": "mind-map-product-run-v1",
            "arguments": {"title": "我的课程脉络"},
        },
    )
    runtime.snapshot = {
        "status": "done",
        "agent_runs": [
            {
                "agent_id": "_edu_7",
                "status": "done",
                "content": '{"summary":"已生成带课程来源的思维导图"}',
            },
            {
                "agent_id": "_edu_5",
                "status": "done",
                "content": '{"summary":"已给出复习顺序"}',
            },
        ],
    }
    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=student,
    )

    assert tool_response.status_code == 200
    assert refreshed.status_code == 200
    run = refreshed.get_json()
    assert run["status"] == "completed"
    note_node = next(
        node for node in run["nodes"] if node["agent_role"] == "note_organizer"
    )
    assert note_node["tool_calls"][0]["tool_name"] == "edu.mind_map.create"
    assert note_node["tool_calls"][0]["status"] == "completed"
    assert "education_run_grant" not in str(run)
    assert raw_grant not in str(run)
