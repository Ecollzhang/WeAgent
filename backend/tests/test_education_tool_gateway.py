from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from services.edu.extensions import db


class ToolGatewayTestConfig:
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
    EDUCATION_TOOL_GRANT_TTL_SECONDS = 900


@pytest.fixture()
def app():
    from services.edu.app import create_edu_app

    application = create_edu_app(ToolGatewayTestConfig)
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
            "title": "Agent evidence lab",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
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


def issue_grant(client, headers, course_id, tools):
    response = client.post(
        "/api/edu/tool-grants",
        headers=headers,
        json={
            "course_id": course_id,
            "allowed_tools": tools,
            "agent_run_id": "agent-run-1",
            "capability_ids": ["builtin-education-actions"],
        },
    )
    assert response.status_code == 201
    return response.get_json()


def invoke(
    client,
    token,
    tool_name,
    arguments=None,
    idempotency_key=None,
    agent_id="_edu_1",
):
    payload = {"arguments": arguments or {}, "agent_id": agent_id}
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    return client.post(
        f"/api/edu/tools/{tool_name}/invoke",
        headers={"X-Education-Run-Grant": token},
        json=payload,
    )


def test_product_write_is_bound_to_its_designated_agent_and_audited(app):
    from services.edu.tool_models import EducationToolCall, EducationToolGrant
    from services.edu.workflow_models import EducationAgentRun

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Evidence and Voice",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    with app.app_context():
        db.session.add(
            EducationAgentRun(
                id="role-bound-courseware-run",
                course_id=course["id"],
                lesson_id=lesson["id"],
                requested_by="teacher",
                workflow_code="product.courseware",
                workflow_name="Agent courseware",
                status="running",
                nodes=[],
                input_payload={},
                output={},
            )
        )
        db.session.commit()
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.courseware.create"],
    )
    with app.app_context():
        stored_grant = EducationToolGrant.query.get(grant["id"])
        stored_grant.agent_run_id = "role-bound-courseware-run"
        db.session.commit()

    wrong_agent = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "kind": "slide_document",
            "schema_name": "weagent.education.slide-document",
            "source_json": {},
            "rendered_html": "",
        },
        "wrong-courseware-agent",
        agent_id="_edu_1",
    )
    designated_agent = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "kind": "slide_document",
            "schema_name": "weagent.education.slide-document",
            "source_json": {},
            "rendered_html": "",
        },
        "designated-courseware-agent",
        agent_id="_edu_2",
    )

    assert wrong_agent.status_code == 403
    assert wrong_agent.get_json()["error_code"] == "agent_not_authorized_for_tool"
    assert designated_agent.status_code == 400
    assert designated_agent.get_json()["error_code"] == "invalid_slide_document"
    with app.app_context():
        rejected = EducationToolCall.query.filter_by(
            grant_id=grant["id"],
            idempotency_key="wrong-courseware-agent",
        ).one()
        assert rejected.agent_id == "_edu_1"
        assert rejected.status == "failed"
        assert rejected.error_code == "agent_not_authorized_for_tool"


def test_runtime_grant_verification_is_opaque_and_actor_scoped(app):
    client = app.test_client()
    teacher, _student, course = setup_course(client, app)
    issued = client.post(
        "/api/edu/tool-grants",
        headers=teacher,
        json={
            "course_id": course["id"],
            "allowed_tools": ["edu.course.context.get"],
            "agent_run_id": "runtime-verification",
            "capability_ids": ["builtin:education_actions"],
        },
    )
    assert issued.status_code == 201
    grant = issued.get_json()

    valid = client.post(
        "/api/edu/tool-grants/verify-runtime",
        headers={"X-Education-Run-Grant": grant["token"]},
        json={"actor_user_id": "teacher"},
    )
    assert valid.status_code == 200
    assert valid.get_json() == {"valid": True}

    wrong_actor = client.post(
        "/api/edu/tool-grants/verify-runtime",
        headers={"X-Education-Run-Grant": grant["token"]},
        json={"actor_user_id": "student"},
    )
    assert wrong_actor.status_code == 403
    assert grant["token"] not in wrong_actor.get_data(as_text=True)

    forged = client.post(
        "/api/edu/tool-grants/verify-runtime",
        headers={"X-Education-Run-Grant": "A" * 48},
        json={"actor_user_id": "teacher"},
    )
    assert forged.status_code == 403
    assert grant["token"] not in forged.get_data(as_text=True)


def question_payload():
    return {
        "title": "Emotion inference",
        "question_type": "single_choice",
        "prompt": "Which emotion is best supported by the paragraph?",
        "options": [
            "Excitement",
            "Nervousness",
            "Mixed excitement and nervousness",
            "Indifference",
        ],
        "difficulty": "easy",
        "score": 5,
        "knowledge_points": ["emotion inference"],
        "correct_answer": "C",
        "explanation": "Both feelings are stated in the text.",
    }


def test_catalog_is_role_filtered_and_does_not_expose_student_writes_to_teacher(
    app,
):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)

    teacher_catalog = client.get(
        f"/api/edu/tools/catalog?course_id={course['id']}",
        headers=teacher,
    )
    student_catalog = client.get(
        f"/api/edu/tools/catalog?course_id={course['id']}",
        headers=student,
    )

    assert teacher_catalog.status_code == 200
    assert student_catalog.status_code == 200
    teacher_tools = {item["name"] for item in teacher_catalog.get_json()["items"]}
    student_tools = {item["name"] for item in student_catalog.get_json()["items"]}
    assert "edu.question_bank.upsert" in teacher_tools
    assert "edu.student_insight.refresh" in teacher_tools
    assert "edu.mock_exam.create" not in teacher_tools
    assert "edu.mock_exam.create" in student_tools
    assert "edu.question_bank.upsert" not in student_tools


def test_grant_cannot_widen_actor_course_or_allowed_tool(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    other_course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Other course",
            "subject_code": "primary_chinese",
            "grade_band": "primary",
        },
    ).get_json()
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.course.context.get"],
    )

    forged = invoke(
        client,
        grant["token"],
        "edu.course.context.get",
        {
            "course_id": other_course["id"],
            "actor_user_id": "attacker",
        },
    )
    unavailable = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {"questions": [question_payload()]},
        "question-1",
    )

    assert forged.status_code == 400
    assert forged.get_json()["error_code"] == "tool_scope_argument_forbidden"
    assert unavailable.status_code == 403
    assert unavailable.get_json()["error_code"] == "tool_not_granted"


def test_expired_grant_is_rejected_before_dispatch(app):
    from services.edu.tool_models import EducationToolGrant

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.course.context.get"],
    )
    with app.app_context():
        record = EducationToolGrant.query.filter_by(id=grant["id"]).one()
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

    response = invoke(
        client,
        grant["token"],
        "edu.course.context.get",
    )

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "tool_grant_expired"


def test_teacher_question_tool_uses_canonical_service_and_is_idempotent(app):
    from services.edu.knowledge_models import AssessmentItem
    from services.edu.tool_models import EducationToolCall

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.question_bank.upsert", "edu.question_bank.search"],
    )
    arguments = {"questions": [question_payload()], "publish": True}

    first = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        arguments,
        "question-batch-1",
    )
    replay = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        arguments,
        "question-batch-1",
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.get_json()["result"] == replay.get_json()["result"]
    assert replay.get_json()["replayed"] is True
    assert first.get_json()["result"]["items"][0]["status"] == "published"
    with app.app_context():
        assert AssessmentItem.query.count() == 1
        calls = EducationToolCall.query.filter_by(
            grant_id=grant["id"],
            tool_name="edu.question_bank.upsert",
        ).all()
        assert len(calls) == 1
        assert calls[0].status == "completed"
        assert "token" not in str(calls[0].sanitized_input).lower()


def test_student_question_search_uses_published_version_not_teacher_draft(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    created = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json=question_payload(),
    ).get_json()
    assert client.post(
        f"/api/edu/questions/{created['id']}/publish",
        headers=teacher,
    ).status_code == 200
    draft_prompt = "Private teacher draft that students must not retrieve."
    assert client.post(
        f"/api/edu/questions/{created['id']}/versions",
        headers=teacher,
        json={**question_payload(), "prompt": draft_prompt},
    ).status_code == 201
    grant = issue_grant(
        client,
        student,
        course["id"],
        ["edu.question_bank.search"],
    )

    response = invoke(
        client,
        grant["token"],
        "edu.question_bank.search",
        {"limit": 10},
    )

    assert response.status_code == 200
    item = response.get_json()["result"]["items"][0]
    assert item["current_version"]["prompt"] == question_payload()["prompt"]
    assert item["current_version"]["prompt"] != draft_prompt
    assert "answer" not in item["current_version"]


def test_agent_question_group_requires_multiple_children_and_persists_atomically(app):
    from services.edu.knowledge_models import AssessmentItem, AssessmentStimulus

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.question_bank.upsert"],
    )
    stimulus = {
        "client_key": "gift-of-magi",
        "title": "The Gift of the Magi — classroom excerpt",
        "stimulus_type": "reading_passage",
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
        "language": "en",
    }
    one_child = {
        **question_payload(),
        "stimulus_key": "gift-of-magi",
        "stimulus_order": 1,
    }

    rejected = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {"stimuli": [stimulus], "questions": [one_child]},
        "group-too-small",
    )

    assert rejected.status_code == 400
    assert rejected.get_json()["error_code"] == "stimulus_group_too_small"
    with app.app_context():
        assert AssessmentStimulus.query.count() == 0
        assert AssessmentItem.query.count() == 0

    accepted = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {
            "stimuli": [stimulus],
            "questions": [
                one_child,
                {
                    "title": "Evidence response",
                    "question_type": "short_answer",
                    "prompt": "Use one detail to explain Della's situation.",
                    "difficulty": "medium",
                    "score": 5,
                    "knowledge_points": ["text evidence"],
                    "correct_answer": (
                        "She has little money but has saved carefully for Jim."
                    ),
                    "rubric": {"evidence": 3, "explanation": 2},
                    "stimulus_key": "gift-of-magi",
                    "stimulus_order": 2,
                },
            ],
            "publish": True,
        },
        "group-valid",
    )

    assert accepted.status_code == 200
    result = accepted.get_json()["result"]
    assert len(result["stimuli"]) == 1
    assert len(result["items"]) == 2
    assert all(row["status"] == "published" for row in result["items"])


def test_lesson_scoped_run_injects_lesson_into_courseware_write(app):
    from services.edu.tool_models import EducationToolGrant
    from services.edu.workflow_models import EducationAgentRun

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "A Turning Point",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    with app.app_context():
        db.session.add(
            EducationAgentRun(
                id="scoped-agent-run",
                course_id=course["id"],
                lesson_id=lesson["id"],
                requested_by="teacher",
                workflow_code="teacher.preparation",
                workflow_name="Agent courseware",
                status="running",
                nodes=[],
                input_payload={},
                output={},
            )
        )
        db.session.commit()

    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.course.context.get", "edu.courseware.create"],
    )
    with app.app_context():
        stored_grant = EducationToolGrant.query.get(grant["id"])
        stored_grant.agent_run_id = "scoped-agent-run"
        db.session.commit()

    context_response = invoke(
        client,
        grant["token"],
        "edu.course.context.get",
        {},
    )
    assert context_response.status_code == 200
    assert (
        context_response.get_json()["result"]["courseware_context"]["lesson"]["id"]
        == lesson["id"]
    )

    source = {
        "subject_code": "high_school_english",
        "learning_domain": "integrated",
        "text_genre_code": "narrative",
        "lesson_type_code": "reading_writing",
        "title": "A Turning Point",
        "objectives": [
            {"id": "objective-1", "description": "Read for evidence"}
        ],
        "stages": [
            {
                "name": "Close reading",
                "duration_minutes": 20,
                "teacher_activity": "Model evidence selection",
                "student_activity": "Annotate evidence",
                "assessment": "Exit note",
            }
        ],
    }
    response = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "kind": "lesson_plan",
            "schema_name": "weagent.education.lesson-plan",
            "source_json": source,
        },
        "scoped-lesson-plan-v1",
    )

    assert response.status_code == 200
    created = response.get_json()["result"]
    assert created["content"]["lesson_id"] == lesson["id"]
    with app.app_context():
        from services.edu.content_models import EducationContentVersion

        version = EducationContentVersion.query.get(created["version"]["id"])
        assert version.source_agent_run_id == "scoped-agent-run"


def test_courseware_tool_rejects_noncanonical_lesson_plan_objects(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Evidence and Voice",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.courseware.create"],
    )

    response = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "lesson_id": lesson["id"],
            "kind": "lesson_plan",
            "schema_name": "weagent.education.lesson-plan",
            "source_json": {
                "subject_code": "high_school_english",
                "learning_domain": "integrated",
                "text_genre_code": "narrative",
                "lesson_type_code": "reading_writing",
                "title": "Evidence and Voice",
                "objectives": ["Read for evidence"],
                "stages": ["Close reading"],
            },
        },
        "invalid-lesson-plan-v1",
    )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "invalid_lesson_plan"


def test_courseware_tool_returns_page_level_visual_errors_for_agent_repair(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Evidence and Voice",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.courseware.create"],
    )

    response = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "lesson_id": lesson["id"],
            "kind": "slide_document",
            "schema_name": "weagent.education.slide-document",
            "source_json": {
                "title": "Evidence and Voice",
                "theme": {"style": "clear_classroom"},
                "slides": [{
                    "id": "dense-slide",
                    "title": "Too much content",
                    "layout": "content",
                    "blocks": [{
                        "type": "text",
                        "content": "dense content " * 100,
                    }],
                    "speaker_notes": "Repair this page.",
                }],
            },
            "rendered_html": (
                "<!doctype html><html><body><main>"
                + ("preview " * 20)
                + "</main></body></html>"
            ),
        },
        "courseware-visual-repair-v1",
    )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "courseware_visual_quality_failed"
    assert "dense-slide" not in response.get_json()["error"]
    assert "slide_text_too_dense" in response.get_json()["error"]


def test_courseware_tool_requires_warning_free_visual_qa_before_adoption(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    lesson = client.post(
        f"/api/edu/courses/{course['id']}/lessons",
        headers=teacher,
        json={
            "title": "Concise classroom deck",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
        },
    ).get_json()
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.courseware.create"],
    )

    response = invoke(
        client,
        grant["token"],
        "edu.courseware.create",
        {
            "lesson_id": lesson["id"],
            "kind": "slide_document",
            "schema_name": "weagent.education.slide-document",
            "source_json": {
                "title": "Concise classroom deck",
                "theme": {"style": "paper_annotation"},
                "slides": [{
                    "id": "warning-slide",
                    "title": "Evidence",
                    "layout": "content",
                    "blocks": [{
                        "type": "text",
                        "content": "evidence " * 52,
                    }],
                    "speaker_notes": "Shorten this page.",
                }],
            },
            "rendered_html": (
                "<!doctype html><html><body><main>"
                + ("preview " * 20)
                + "</main></body></html>"
            ),
        },
        "courseware-warning-repair-v1",
    )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "courseware_visual_quality_failed"
    assert "slide_text_dense" in response.get_json()["error"]


def test_idempotency_key_reuse_with_different_input_is_rejected(app):
    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.question_bank.upsert"],
    )
    first = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {"questions": [question_payload()]},
        "same-key",
    )
    changed = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {
            "questions": [
                {
                    **question_payload(),
                    "title": "A different question",
                    "prompt": "A different prompt",
                }
            ]
        },
        "same-key",
    )

    assert first.status_code == 200
    assert changed.status_code == 409
    assert changed.get_json()["error_code"] == "idempotency_conflict"


def test_roster_import_supports_partial_rows_and_atomic_rollback(app):
    from services.edu.models import CourseMembership

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.course.members.import"],
    )
    partial = invoke(
        client,
        grant["token"],
        "edu.course.members.import",
        {
            "members": [
                {"user_id": "new-student", "display_name": "新同学"},
                {"user_id": "teacher", "display_name": "不能降级的教师"},
            ],
            "atomic": False,
        },
        "partial-roster",
    )
    atomic = invoke(
        client,
        grant["token"],
        "edu.course.members.import",
        {
            "members": [
                {"user_id": "atomic-student", "display_name": "原子同学"},
                {"user_id": "teacher", "display_name": "不能降级的教师"},
            ],
            "atomic": True,
        },
        "atomic-roster",
    )

    assert partial.status_code == 200
    partial_result = partial.get_json()["result"]
    assert partial_result["imported_count"] == 1
    assert partial_result["failed_count"] == 1
    assert partial_result["failures"][0]["error_code"] == "member_role_conflict"
    assert atomic.status_code == 409
    assert atomic.get_json()["error_code"] == "member_role_conflict"
    with app.app_context():
        assert CourseMembership.query.filter_by(
            course_id=course["id"],
            user_id="new-student",
            status="active",
        ).count() == 1
        assert CourseMembership.query.filter_by(
            course_id=course["id"],
            user_id="atomic-student",
        ).count() == 0


def test_student_grant_creates_real_private_mock_exam_and_weakness_snapshot(app):
    client = app.test_client()
    teacher, student, course = setup_course(client, app)
    question = client.post(
        f"/api/edu/courses/{course['id']}/questions",
        headers=teacher,
        json=question_payload(),
    ).get_json()
    assert client.post(
        f"/api/edu/questions/{question['id']}/publish",
        headers=teacher,
    ).status_code == 200
    grant = issue_grant(
        client,
        student,
        course["id"],
        ["edu.mock_exam.create", "edu.weakness.analyze"],
    )

    exam = invoke(
        client,
        grant["token"],
        "edu.mock_exam.create",
        {"question_count": 1, "duration_minutes": 10},
        "student-exam-1",
    )
    weakness = invoke(
        client,
        grant["token"],
        "edu.weakness.analyze",
        {},
        "student-weakness-1",
    )

    assert exam.status_code == 200
    assert exam.get_json()["result"]["student_user_id"] == "student"
    assert len(exam.get_json()["result"]["questions"]) == 1
    assert weakness.status_code == 200
    assert weakness.get_json()["result"]["student_user_id"] == "student"
    assert weakness.get_json()["result"]["data_state"] == "insufficient"


def test_failed_tool_call_is_audited_without_leaking_grant(app):
    from services.edu.tool_models import EducationToolCall

    client = app.test_client()
    teacher, _, course = setup_course(client, app)
    grant = issue_grant(
        client,
        teacher,
        course["id"],
        ["edu.question_bank.upsert"],
    )

    response = invoke(
        client,
        grant["token"],
        "edu.question_bank.upsert",
        {
            "questions": [
                {
                    **question_payload(),
                    "options": ["A. Wrong", "B. Still wrong"],
                }
            ]
        },
        "invalid-question",
    )

    assert response.status_code == 400
    with app.app_context():
        call = EducationToolCall.query.filter_by(
            grant_id=grant["id"],
            idempotency_key="invalid-question",
        ).one()
        assert call.status == "failed"
        assert call.error_code == "non_canonical_options"
        assert grant["token"] not in str(call.sanitized_input)
