from datetime import timedelta
import re

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
        visible_prompt=None,
        workspace_role=None,
        agent_ids,
        workflow,
        education_run_grant=None,
        services=None,
        agent_service_views=None,
    ):
        index = len(self.started) + 1
        self.started.append(
            {
                "authorization": authorization,
                "title": title,
                "prompt": prompt,
                "visible_prompt": visible_prompt,
                "workspace_role": workspace_role,
                "agent_ids": agent_ids,
                "workflow": workflow,
                "education_run_grant": education_run_grant,
                "services": services,
                "agent_service_views": agent_service_views,
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
    assert '<tool_call>{"name":"education_action"' in started["prompt"]
    assert "Action-specific fields MUST be nested under args.arguments" in (
        started["prompt"]
    )
    assert started["workspace_role"] == "student"
    assert "edu.mock_exam.create" not in started["visible_prompt"]
    assert "模拟考试" in started["visible_prompt"]
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
            "options": {
                "requirements": "突出故事弧和读写迁移",
                "theme_style": "paper_annotation",
            },
        },
    )

    assert missing_lesson.status_code == 400
    assert forbidden.status_code == 403
    assert created.status_code == 202
    run = created.get_json()
    assert run["lesson_id"] == lesson["id"]
    assert run["product_code"] == "courseware"
    assert run["business_route"] == {
        "path": "/education/teacher/courseware",
        "query": {"courseId": course["id"], "lessonId": lesson["id"]},
    }
    assert [node["agent_role"] for node in run["nodes"]] == [
        "course_designer",
        "courseware_maker",
        "teaching_reviewer",
    ]
    started = runtime.started[0]
    assert started["workspace_role"] == "teacher"
    assert "根据当前教案生成 PPT" in started["visible_prompt"]
    assert "edu.courseware.create" not in started["visible_prompt"]
    assert re.fullmatch(
        r"高中英语阅读与写作｜Education·校园生活叙事阅读"
        r"（Agent 课件制作）｜\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
        started["title"],
    )
    assert started["agent_ids"] == ["_edu_1", "_edu_2", "_edu_9"]
    assert started["workflow"]["execution_mode"] == "server_defined"
    assert "edu.courseware.create" in started["prompt"]
    assert "slide_document" in started["prompt"]
    assert "Education large-artifact finalizer protocol" in started["prompt"]
    assert "slide_document.json and preview.html" in started["prompt"]
    assert "trusted server workflow" in started["prompt"]
    assert "Return exactly two fenced file blocks" in started["prompt"]
    assert "The trusted runtime writes those blocks into your private workspace" in (
        started["prompt"]
    )
    assert "<tool_call>" not in started["prompt"]
    assert "lesson_id is injected from the lesson-scoped Agent run" in (
        started["prompt"]
    )
    assert "不得创建 .js" in started["prompt"]
    assert '{"style":"paper_annotation"}' in started["prompt"]
    assert (
        "text, bullets, heading, subheading, quote, key-point, question, "
        "tip, image, table, timeline, comparison, vocabulary, activity"
    ) in started["prompt"]
    assert "Do not use instruction, list, title, paragraph" in started["prompt"]
    assert "Each block permits only type, content, emphasis, source_ref" in (
        started["prompt"]
    )
    assert lesson["id"] not in started["prompt"]
    assert "不得自动发布" in started["prompt"]
    finalizer_node = next(
        node
        for node in started["workflow"]["nodes"]
        if node["agent_id"] == "_edu_2"
    )
    assert finalizer_node["finalizer"] == {
        "type": "education_courseware_from_agent_files"
    }

    invalid_theme = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "lesson_id": lesson["id"],
            "product_code": "courseware",
            "options": {"theme_style": "model_invented_css"},
        },
    )
    assert invalid_theme.status_code == 400
    assert "supported presentation style" in invalid_theme.get_json()["error"]


def test_teacher_student_insight_uses_trusted_refresh_finalizer(education_app):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, teacher, _, _ = seed_course(education_app)

    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "student_insight",
            "options": {},
        },
    )

    assert created.status_code == 202
    run = created.get_json()
    assert run["nodes"][0]["finalizer"] == {
        "type": "education_student_insight_refresh_from_agent_reply"
    }
    started = runtime.started[0]
    assert "Education trusted reply finalizer protocol" in started["prompt"]
    assert '{"refresh":true}' in started["prompt"]
    assert "Do not call education_action" in started["prompt"]
    assert "<tool_call>" not in started["prompt"]


def test_teacher_starts_submission_review_agent_with_natural_visible_prompt(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, student, _ = seed_course(education_app)
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Evidence paragraph",
            "kind": "writing",
            "instruction_json": {"text": "Explain the turning point."},
            "evaluation_json": {"rubric": {"evidence": 5, "reasoning": 5}},
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    submitted = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student,
        json={"answer_json": {"writing": "The choice changes the ending."}},
    ).get_json()["submission"]

    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "submission_review",
            "options": {"submission_id": submitted["id"]},
        },
    )

    assert created.status_code == 202
    run = created.get_json()
    assert run["workflow_code"] == "product.submission_review"
    assert run["business_route"]["path"].endswith(
        f"/assignments/{assignment['id']}/review/{submitted['id']}"
    )
    assert [node["agent_role"] for node in run["nodes"]] == [
        "learning_analyst",
        "teaching_reviewer",
    ]
    assert run["nodes"][0]["finalizer"] == {
        "type": "education_submission_review_from_agent_reply"
    }
    assert run["nodes"][1]["finalizer"] == {
        "type": "education_submission_review_reviewer_from_agent_reply"
    }
    started = runtime.started[0]
    assert "edu.submission_review.context.get" in started["prompt"]
    assert "edu.submission_review.analysis.create" in started["prompt"]
    assert '"strengths":["string"]' in started["prompt"]
    assert '"evidence":"exact quote"' in started["prompt"]
    assert '"concern":"string"' in started["prompt"]
    assert '"evidence_refs":["exact quote"]' in started["prompt"]
    assert '"verdict":"approved|needs_revision"' in started["prompt"]
    assert '"required_changes":["string"]' in started["prompt"]
    assert submitted["id"] in started["prompt"]
    assert submitted["id"] not in started["visible_prompt"]
    assert started["visible_prompt"] == "为当前学生提交生成可采纳的批改建议"


def test_submission_review_agent_persists_evidence_linked_cached_analysis(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, student, _ = seed_course(education_app)
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Evidence paragraph",
            "kind": "writing",
            "instruction_json": {"text": "Explain the turning point."},
            "evaluation_json": {"rubric": {"evidence": 5, "reasoning": 5}},
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    submitted = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student,
        json={"answer_json": {"writing": "The choice changes the ending."}},
    ).get_json()["submission"]
    run = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "submission_review",
            "options": {"submission_id": submitted["id"]},
        },
    ).get_json()
    grant = runtime.started[0]["education_run_grant"]

    context = client.post(
        "/api/edu/tools/edu.submission_review.context.get/invoke",
        headers={"X-Education-Run-Grant": grant},
        json={
            "agent_id": "_edu_4",
            "arguments": {"submission_id": submitted["id"]},
        },
    )
    assert context.status_code == 200
    assert context.get_json()["result"]["answer_json"]["writing"].startswith("The choice")

    analysis_payload = {
        "summary": "The response identifies the turning point but needs reasoning.",
        "strengths": ["Identifies the decisive choice"],
        "issues": [
            {
                "evidence": "The choice changes the ending.",
                "concern": "The causal link is asserted but not explained.",
                "suggestion": "Add one sentence connecting the choice to the result.",
            }
        ],
        "next_steps": ["Use evidence → reasoning → conclusion"],
        "evidence_refs": ["The choice changes the ending."],
    }
    created = client.post(
        "/api/edu/tools/edu.submission_review.analysis.create/invoke",
        headers={"X-Education-Run-Grant": grant},
        json={
            "agent_id": "_edu_4",
            "idempotency_key": "review-analysis-v1",
            "arguments": {
                "analysis": analysis_payload,
            },
        },
    )
    assert created.status_code == 200
    assert created.get_json()["result"]["analysis_json"] == analysis_payload

    review = client.get(
        f"/api/edu/submissions/{submitted['id']}/review",
        headers=teacher,
    ).get_json()
    assert review["analysis_state"] == "ready"
    assert review["analysis"]["agent_run_id"] == run["id"]
    assert review["analysis"]["analysis_json"]["issues"][0]["evidence"].startswith(
        "The choice"
    )


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
            "confirmed_actions": ["edu.course.members.import"],
        },
    )
    forbidden = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "roster_import",
            "options": {"members": members},
            "confirmed_actions": ["edu.course.members.import"],
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


def test_product_run_history_and_conversation_context_are_bidirectional(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, _, teacher, student, other_student = seed_course(education_app)

    first = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "course_mind_map",
            "options": {"title": "第一次课程导图"},
        },
    ).get_json()
    second = client.post(
        "/api/edu/product-agent-runs",
        headers=student,
        json={
            "course_id": course["id"],
            "product_code": "course_mind_map",
            "options": {"title": "第二次课程导图"},
        },
    ).get_json()

    history = client.get(
        f"/api/edu/courses/{course['id']}/product-agent-runs"
        "?product_code=course_mind_map",
        headers=student,
    )
    context = client.get(
        f"/api/edu/conversations/{second['conversation_id']}/product-context",
        headers=student,
    )
    peer_context = client.get(
        f"/api/edu/conversations/{second['conversation_id']}/product-context",
        headers=other_student,
    )
    teacher_context = client.get(
        f"/api/edu/conversations/{second['conversation_id']}/product-context",
        headers=teacher,
    )

    assert history.status_code == 200
    history_body = history.get_json()
    assert history_body["total"] == 2
    assert [item["id"] for item in history_body["items"]] == [
        second["id"],
        first["id"],
    ]
    assert context.status_code == 200
    context_body = context.get_json()
    assert context_body["course"] == {
        "id": course["id"],
        "title": "高中英语阅读与写作",
        "membership_role": "student",
    }
    assert context_body["run"]["id"] == second["id"]
    assert context_body["run"]["product_code"] == "course_mind_map"
    assert context_body["run"]["business_route"] == {
        "path": "/education/student/mind-maps",
        "query": {"courseId": course["id"]},
    }
    assert context_body["progress"]["agent_count"] == 2
    assert context_body["progress"]["completed_count"] == 0
    assert peer_context.status_code == 404
    assert teacher_context.status_code == 404


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
    assert run["output"]["adopted_object"]["object_type"] == "course_mind_map"
    assert run["output"]["adopted_object"]["object_id"]
    assert run["output"]["adopted_object"]["version_id"]
    assert run["output"]["adopted_object"]["preview_kind"] == "mind_map"
    assert "education_run_grant" not in str(run)
    assert raw_grant not in str(run)


def test_product_run_without_required_durable_tool_write_is_partial(education_app):
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
            "options": {"title": "My course map"},
        },
    ).get_json()
    runtime.snapshot = {
        "status": "done",
        "agent_runs": [
            {
                "agent_id": "_edu_7",
                "status": "done",
                "content": '{"summary":"drafted a map"}',
            },
            {
                "agent_id": "_edu_5",
                "status": "done",
                "content": '{"summary":"reviewed the map"}',
            },
        ],
    }

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=student,
    )

    assert refreshed.status_code == 200
    run = refreshed.get_json()
    assert run["status"] == "partial"
    assert "edu.mind_map.create" in run["error_summary"]
    assert "未写入" in run["error_summary"]


def test_product_run_with_failed_agent_reaches_terminal_partial_state(education_app):
    from services.edu.tool_models import EducationToolGrant

    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, student, _ = seed_course(education_app)
    assignment = client.post(
        f"/api/edu/lessons/{lesson['id']}/assignments",
        headers=teacher,
        json={
            "title": "Review terminal state",
            "kind": "writing",
            "instruction_json": {"text": "Explain the evidence."},
            "evaluation_json": {"rubric": {"evidence": 10}},
        },
    ).get_json()
    client.post(f"/api/edu/assignments/{assignment['id']}/publish", headers=teacher)
    submission = client.post(
        f"/api/edu/assignments/{assignment['id']}/submissions",
        headers=student,
        json={"answer_json": {"writing": "A short response."}},
    ).get_json()["submission"]
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "product_code": "submission_review",
            "options": {"submission_id": submission["id"]},
        },
    ).get_json()
    runtime.snapshot = {
        "status": "done",
        "agent_runs": [
            {
                "agent_id": "_edu_4",
                "status": "done",
                "content": '{"summary":"analysis attempted"}',
            },
            {
                "agent_id": "_edu_9",
                "status": "error",
                "error": "reviewer failed",
            },
        ],
    }

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=teacher,
    )

    assert refreshed.status_code == 200
    run = refreshed.get_json()
    assert run["status"] == "partial"
    assert run["finished_at"] is not None
    assert "reviewer failed" in run["error_summary"]
    with education_app.app_context():
        grant = EducationToolGrant.query.filter_by(
            agent_run_id=created["id"]
        ).one()
        assert grant.revoked_at is not None


def test_product_run_skips_shared_artifact_repair_and_requires_designated_writer(
    education_app,
):
    from services.edu.tool_models import EducationToolCall, EducationToolGrant

    runtime = FakeProductRuntime()

    def forbidden_workspace_read(**_kwargs):
        raise AssertionError("product workflows must not inspect collaboration drafts")

    runtime.get_workspace_json = forbidden_workspace_read
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, _, _ = seed_course(education_app)
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "lesson_id": lesson["id"],
            "product_code": "courseware",
            "options": {"requirements": "make a concise deck"},
        },
    ).get_json()
    with education_app.app_context():
        grant = EducationToolGrant.query.filter_by(
            agent_run_id=created["id"]
        ).one()
        db.session.add(
            EducationToolCall(
                grant_id=grant.id,
                course_id=course["id"],
                actor_user_id="teacher",
                agent_id="_edu_1",
                tool_name="edu.courseware.create",
                idempotency_key="historical-wrong-agent-write",
                input_hash="test",
                sanitized_input={},
                status="completed",
                result_json={"content": {"id": "wrong-agent-content"}},
            )
        )
        db.session.commit()
    runtime.snapshot = {
        "status": "done",
        "agent_runs": [
            {
                "agent_id": agent_id,
                "status": "done",
                "content": '{"summary":"collaboration complete"}',
            }
            for agent_id in ("_edu_1", "_edu_2", "_edu_9")
        ],
    }

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=teacher,
    )

    assert refreshed.status_code == 200
    run = refreshed.get_json()
    assert run["status"] == "partial"
    assert "edu.courseware.create" in run["error_summary"]


def test_invalid_courseware_write_keeps_an_editable_recoverable_draft(
    education_app,
):
    runtime = FakeProductRuntime()
    education_app.extensions["education_runtime_client"] = runtime
    client = education_app.test_client()
    course, lesson, teacher, _, _ = seed_course(education_app)
    created = client.post(
        "/api/edu/product-agent-runs",
        headers=teacher,
        json={
            "course_id": course["id"],
            "lesson_id": lesson["id"],
            "product_code": "courseware",
            "options": {"requirements": "make a concise deck"},
        },
    ).get_json()
    raw_grant = runtime.started[-1]["education_run_grant"]
    invalid_source = {
        "title": "Campus Life",
        "theme": {"style": "editorial"},
        "slides": "not-an-array",
    }
    rejected = client.post(
        "/api/edu/tools/edu.courseware.create/invoke",
        headers={"X-Education-Run-Grant": raw_grant},
        json={
            "agent_id": "_edu_2",
            "idempotency_key": "product-courseware-slide-invalid-v1",
            "arguments": {
                "kind": "slide_document",
                "schema_name": "weagent.education.slide-document",
                "source_json": invalid_source,
                "rendered_html": "<h1>Campus Life</h1>",
            },
        },
    )
    runtime.snapshot = {
        "status": "done",
        "agent_runs": [
            {
                "agent_id": "_edu_2",
                "status": "done",
                "content": '{"summary":"courseware draft ready"}',
            },
            {
                "agent_id": "_edu_1",
                "status": "error",
                "error": "review deferred",
                "content": "",
            },
            {
                "agent_id": "_edu_9",
                "status": "error",
                "error": "review deferred",
                "content": "",
            },
        ],
    }

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=teacher,
    )

    assert rejected.status_code == 400
    run = refreshed.get_json()
    assert run["status"] == "partial"
    draft = run["output"]["recoverable_draft"]
    assert draft["kind"] == "slide_document"
    assert draft["source_json"] == invalid_source
    assert draft["validation_error"]


def test_moderator_plan_does_not_end_run_before_workers_are_visible(education_app):
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
            "options": {},
        },
    ).get_json()
    runtime.snapshot = {
        "status": "running",
        "agent_runs": [
            {
                "agent_id": "moderator",
                "status": "done",
                "content": (
                    'provider note\n{"type":"plan","tasks":['
                    '{"task_id":"map","agent_id":"_edu_7"}]}'
                ),
            }
        ],
    }

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=student,
    )

    assert refreshed.status_code == 200
    assert refreshed.get_json()["status"] == "running"


def test_legacy_completed_product_run_is_reconciled_when_write_is_missing(
    education_app,
):
    from services.edu.workflow_models import EducationAgentRun

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
            "options": {},
        },
    ).get_json()
    with education_app.app_context():
        stored = EducationAgentRun.query.filter_by(id=created["id"]).first()
        stored.status = "completed"
        db.session.commit()

    refreshed = client.get(
        f"/api/edu/product-agent-runs/{created['id']}",
        headers=student,
    )

    assert refreshed.status_code == 200
    assert refreshed.get_json()["status"] == "partial"
