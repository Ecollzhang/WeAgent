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
                    },
                },
                201,
            )
        return FakeResponse({"code": 201, "data": {"id": "message-1"}}, 201)

    monkeypatch.setattr("services.edu.runtime_client.requests.request", fake_request)
    client = CoreRuntimeClient(base_url="http://core", agent_adapter="codex")

    client.start_workflow(
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
    assert "opaque-run-grant" not in requests[1][2]["json"]["content"]


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
