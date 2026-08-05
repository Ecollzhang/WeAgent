import json

import pytest

from services.edu.runtime_client import CoreRuntimeClient, CoreRuntimeError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeRawResponse(FakeResponse):
    def __init__(self, payload, status_code=200):
        super().__init__(None, status_code)
        self.content = payload


def test_education_runtime_selects_codex_adapter_for_deepseek_team(monkeypatch):
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if url.endswith("/api/conversations"):
            return FakeResponse(
                {
                    "code": 201,
                    "data": {
                        "id": "conversation-1",
                        "sandbox_session_id": "sandbox-1",
                        "sandbox_runtime": {"generation": 3},
                    },
                },
                201,
            )
        if url.endswith("/runtime-preflight"):
            return FakeResponse(
                {
                    "code": 200,
                    "data": {
                        "ready": True,
                        "required_tools": ["education_action"],
                    },
                }
            )
        return FakeResponse({"code": 201, "data": {"id": "message-1"}}, 201)

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core", agent_adapter="codex")

    started = client.start_workflow(
        authorization="Bearer token",
        title="Lesson run",
        prompt="Build lesson",
        agent_ids=["_edu_1", "_edu_3"],
        workflow={"id": "reading_lesson"},
        education_run_grant="opaque-run-grant-1234567890",
    )

    conversation_payload = requests[0][2]["json"]
    assert conversation_payload["agent_configs"] == {
        "_edu_1": {
            "adapter_name": "codex",
            "education_tool_context": {
                "run_grant": "opaque-run-grant-1234567890"
            },
        },
        "_edu_3": {
            "adapter_name": "codex",
            "education_tool_context": {
                "run_grant": "opaque-run-grant-1234567890"
            },
        },
        "moderator": {
            "adapter_name": "codex",
            "education_tool_context": {
                "run_grant": "opaque-run-grant-1234567890"
            },
        },
    }
    assert requests[1][0] == "GET"
    assert requests[1][1].endswith(
        "/api/conversations/conversation-1/runtime-preflight"
    )
    assert requests[1][2]["params"] == {
        "required_tools": "education_action",
        "agent_ids": "_edu_1,_edu_3",
    }
    assert "opaque-run-grant" not in requests[2][2]["json"]["content"]
    assert started["runtime_generation"] == 3


def test_education_runtime_persists_context_before_tool_preflight(monkeypatch):
    order = []

    def fake_request(method, url, **kwargs):
        if url.endswith("/api/conversations"):
            order.append("conversation_created")
            return FakeResponse(
                {
                    "code": 201,
                    "data": {
                        "id": "conversation-1",
                        "sandbox_session_id": "sandbox-1",
                    },
                },
                201,
            )
        if url.endswith("/runtime-preflight"):
            order.append("runtime_preflight")
            return FakeResponse({"code": 200, "data": {"ready": True}})
        order.append("message_dispatched")
        return FakeResponse({"code": 201, "data": {"id": "message-1"}}, 201)

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    client.start_workflow(
        authorization="Bearer token",
        title="Student insight run",
        prompt="Analyze the class",
        workspace_role="teacher",
        agent_ids=["_edu_4"],
        workflow={"id": "student_insight"},
        education_run_grant="opaque-run-grant-1234567890",
        on_conversation_created=lambda conversation: order.append(
            f"context_persisted:{conversation['id']}"
        ),
    )

    assert order == [
        "conversation_created",
        "context_persisted:conversation-1",
        "runtime_preflight",
        "message_dispatched",
    ]


def test_education_runtime_keeps_visible_intent_separate_from_execution_context(
    monkeypatch,
):
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if url.endswith("/api/conversations"):
            return FakeResponse(
                {
                    "code": 201,
                    "data": {
                        "id": "conversation-1",
                        "sandbox_session_id": "sandbox-1",
                    },
                },
                201,
            )
        if url.endswith("/runtime-preflight"):
            return FakeResponse(
                {"code": 200, "data": {"ready": True}}
            )
        return FakeResponse({"code": 201, "data": {"id": "message-1"}}, 201)

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    client.start_workflow(
        authorization="Bearer token",
        title="Courseware run",
        prompt="INTERNAL TOOL AND SCHEMA CONTRACT",
        visible_prompt="根据当前教案生成 PPT，使用纸张批注风格。",
        workspace_role="teacher",
        agent_ids=["_edu_1", "_edu_2"],
        workflow={"id": "courseware"},
        education_run_grant="opaque-run-grant-1234567890",
    )

    conversation_payload = requests[0][2]["json"]
    message_payload = requests[2][2]["json"]
    assert conversation_payload["workspace_context"] == {
        "domain": "edu",
        "role": "teacher",
    }
    assert message_payload["content"] == "根据当前教案生成 PPT，使用纸张批注风格。"
    assert message_payload["execution_context"] == "INTERNAL TOOL AND SCHEMA CONTRACT"
    assert "INTERNAL TOOL" not in message_payload["content"]


def test_education_runtime_aborts_before_message_when_tool_preflight_fails(
    monkeypatch,
):
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if url.endswith("/api/conversations"):
            return FakeResponse(
                {
                    "code": 201,
                    "data": {
                        "id": "conversation-1",
                        "sandbox_session_id": "sandbox-1",
                    },
                },
                201,
            )
        if url.endswith("/runtime-preflight"):
            return FakeResponse(
                {
                    "code": 200,
                    "data": {
                        "ready": False,
                        "missing_tools": ["education_action"],
                    },
                }
            )
        return FakeResponse({"code": 200, "data": {"deleted": True}})

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core", agent_adapter="codex")

    with pytest.raises(CoreRuntimeError, match="education_action"):
        client.start_workflow(
            authorization="Bearer token",
            title="Lesson run",
            prompt="Build lesson",
            agent_ids=["_edu_2"],
            workflow={"id": "courseware"},
            education_run_grant="opaque-run-grant-1234567890",
        )

    assert [request[0] for request in requests] == ["POST", "GET", "DELETE"]


def test_education_runtime_reads_structured_json_from_shared_sandbox(monkeypatch):
    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "http://core/api/sandbox/sessions/sandbox-1/files/raw"
        assert kwargs["params"] == {"path": "/workspace/shared/lesson_plan_draft.json"}
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        return FakeRawResponse(b'{"objectives":["Read for evidence"]}')

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    result = client.get_workspace_json(
        authorization="Bearer token",
        sandbox_session_id="sandbox-1",
        path="/workspace/shared/lesson_plan_draft.json",
    )

    assert result == {"objectives": ["Read for evidence"]}


def test_lesson_plan_artifact_accepts_only_canonical_teacher_schema(monkeypatch):
    payload = {
        "subject_code": "high_school_english",
        "learning_domain": "integrated",
        "text_genre_code": "narrative",
        "lesson_type_code": "reading_writing",
        "title": "A Turning Point",
        "objectives": [
            {
                "id": "objective-1",
                "description": "Infer emotion changes from textual evidence",
            }
        ],
        "stages": [
            {
                "name": "Close reading",
                "duration_minutes": 20,
                "teacher_activity": "Model evidence selection",
                "student_activity": "Annotate the turning point",
                "assessment": "Evidence note",
            }
        ],
    }

    monkeypatch.setattr(
        "services.edu.runtime_client.requests.request",
        lambda *_args, **_kwargs: FakeRawResponse(
            json.dumps(payload).encode("utf-8")
        ),
    )
    client = CoreRuntimeClient(base_url="http://core")

    result = client.get_workspace_json(
        authorization="Bearer token",
        sandbox_session_id="sandbox-1",
        path="/workspace/shared/lesson_plan_draft.json",
        artifact_role="course_designer",
    )

    assert result["objectives"][0]["id"] == "objective-1"
    assert result["stages"][0]["duration_minutes"] == 20


@pytest.mark.parametrize(
    "payload",
    [
        {
            "meta": {"subject_code": "high_school_english"},
            "content": {
                "objectives": ["Read for evidence"],
                "activities": "Close reading",
                "assessment": "Exit ticket",
            },
        },
        {
            "subject_code": "high_school_english",
            "learning_domain": "integrated",
            "text_genre_code": "narrative",
            "objectives": ["Read for evidence"],
            "stages": [{"name": "Close reading"}],
        },
    ],
)
def test_lesson_plan_artifact_rejects_legacy_or_ambiguous_schema(
    monkeypatch,
    payload,
):
    monkeypatch.setattr(
        "services.edu.runtime_client.requests.request",
        lambda *_args, **_kwargs: FakeRawResponse(
            json.dumps(payload).encode("utf-8")
        ),
    )
    client = CoreRuntimeClient(base_url="http://core")

    with pytest.raises(CoreRuntimeError, match="lesson plan artifact"):
        client.get_workspace_json(
            authorization="Bearer token",
            sandbox_session_id="sandbox-1",
            path="/workspace/shared/lesson_plan_draft.json",
            artifact_role="course_designer",
        )


def test_education_runtime_fetches_public_profiles_in_one_request(monkeypatch):
    def fake_request(method, url, **kwargs):
        assert method == "POST"
        assert url.endswith("/api/auth/profiles")
        assert kwargs["json"] == {"user_ids": ["teacher-1", "student-1"]}
        return FakeResponse(
            {
                "code": 200,
                "data": {
                    "items": [
                        {"id": "teacher-1", "username": "王老师", "avatar_url": ""},
                        {"id": "student-1", "username": "小林", "avatar_url": ""},
                    ]
                },
            }
        )

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    profiles = client.get_user_profiles(
        authorization="Bearer token",
        user_ids=["teacher-1", "student-1"],
    )

    assert profiles["teacher-1"]["username"] == "王老师"


def test_invalid_agent_json_is_sent_back_to_the_same_agent_for_repair(monkeypatch):
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if method == "POST":
            assert url.endswith("/api/sandbox/sessions/sandbox-1/send")
            assert kwargs["json"]["agent_id"] == "_edu_3"
            assert "exercises_draft.json" in kwargs["json"]["message"]
            return FakeResponse({"code": 200, "data": {"status": "done"}})
        return FakeRawResponse(b'{"exercises":[{"question":"valid"}]}')

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    result = client.repair_workspace_json(
        authorization="Bearer token",
        sandbox_session_id="sandbox-1",
        agent_id="_edu_3",
        path="/workspace/shared/exercises_draft.json",
        validation_error="unescaped quote at line 12",
    )

    assert result["exercises"][0]["question"] == "valid"
    assert [request[0] for request in requests] == ["POST", "GET"]


def test_exercise_artifact_rejects_a_file_path_receipt_instead_of_questions(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeRawResponse(
            '{"text":"generated /workspace/shared/exercises_draft.js"}'.encode("utf-8")
        )

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    with pytest.raises(CoreRuntimeError, match="questions"):
        client.get_workspace_json(
            authorization="Bearer token",
            sandbox_session_id="sandbox-1",
            path="/workspace/shared/exercises_draft.json",
            artifact_role="exercise_generator",
        )


def test_exercise_artifact_accepts_renderable_questions(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeRawResponse(
            b'{"meta":{"title":"Practice","estimated_minutes":10,"total_score":5},'
            b'"questions":[{"id":"Q1","type":"short_answer","prompt":"Why?",'
            b'"answer":"Because.","difficulty":"easy","score":5}]}'
        )

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    result = client.get_workspace_json(
        authorization="Bearer token",
        sandbox_session_id="sandbox-1",
        path="/workspace/shared/exercises_draft.json",
        artifact_role="exercise_generator",
    )

    assert result["questions"][0]["prompt"] == "Why?"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_exercise_artifact_accepts_agent_difficulty_vocabulary(
    monkeypatch, difficulty
):
    def fake_request(method, url, **kwargs):
        payload = {
            "questions": [
                {
                    "id": "Q1",
                    "type": "multiple_choice",
                    "prompt": "What is the main idea?",
                    "options": ["A", "B"],
                    "answer": "A",
                    "difficulty": difficulty,
                    "score": 5,
                }
            ]
        }
        return FakeRawResponse(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    result = client.get_workspace_json(
        authorization="Bearer token",
        sandbox_session_id="sandbox-1",
        path="/workspace/shared/exercises_draft.json",
        artifact_role="exercise_generator",
    )

    assert result["questions"][0]["difficulty"] == difficulty


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("difficulty", "basic"),
        ("difficulty", "基础"),
        ("type", "choice"),
        ("type", "选择题"),
    ],
)
def test_exercise_artifact_rejects_noncanonical_enums(monkeypatch, field, value):
    question = {
        "id": "Q1",
        "type": "single_choice",
        "prompt": "What is the main idea?",
        "options": ["First answer", "Second answer"],
        "answer": "A",
        "difficulty": "easy",
        "score": 5,
    }
    question[field] = value

    def fake_request(method, url, **kwargs):
        return FakeRawResponse(
            json.dumps({"questions": [question]}).encode("utf-8")
        )

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    with pytest.raises(CoreRuntimeError, match=field):
        client.get_workspace_json(
            authorization="Bearer token",
            sandbox_session_id="sandbox-1",
            path="/workspace/shared/exercises_draft.json",
            artifact_role="exercise_generator",
        )


def test_exercise_artifact_rejects_option_labels_inside_option_text(monkeypatch):
    payload = {
        "questions": [
            {
                "id": "Q1",
                "type": "single_choice",
                "prompt": "What is the main idea?",
                "options": ["A. First answer", "B. Second answer"],
                "answer": "A",
                "difficulty": "easy",
                "score": 5,
            }
        ]
    }

    def fake_request(method, url, **kwargs):
        return FakeRawResponse(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core")

    with pytest.raises(CoreRuntimeError, match="plain text"):
        client.get_workspace_json(
            authorization="Bearer token",
            sandbox_session_id="sandbox-1",
            path="/workspace/shared/exercises_draft.json",
            artifact_role="exercise_generator",
        )
