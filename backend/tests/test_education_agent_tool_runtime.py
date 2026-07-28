import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import AgentCapabilityBinding, Capability
from app.sandbox.container import tools as container_tools
from app.sandbox.container.capabilities import write_projection, write_run_snapshot
from app.services.agent_service import agent_service
from app.services.builtin_tool_definitions import get_builtin_tool_definition
from app.services.capability_projection_service import build_capability_projection
from app.services.capability_service import capability_service
from app.services.conversation_service import _trusted_education_runtime_env


def test_education_action_is_a_real_bounded_builtin_tool_definition():
    definition = get_builtin_tool_definition("education_actions")

    assert definition["status"] == "implemented"
    assert definition["tool_names"] == ["education_action"]
    assert definition["permissions"]["required"] == ["network"]
    assert (
        definition["manifest"]["input_schema"]["properties"]["action"]["enum"]
        == [
            "edu.course.list",
            "edu.course.members.list",
            "edu.course.context.get",
            "edu.question_bank.search",
            "edu.knowledge.search",
            "edu.course.create",
            "edu.course.members.import",
            "edu.lesson.create",
            "edu.courseware.create",
            "edu.asset.attach",
            "edu.question_bank.upsert",
            "edu.paper.compose",
            "edu.student_insight.refresh",
            "edu.mock_exam.create",
            "edu.weakness.analyze",
            "edu.mind_map.create",
        ]
    )


def test_education_runtime_context_is_not_added_outside_education_sessions():
    configs = {
        "_edu_1": {
            "education_tool_context": {
                "run_grant": "A" * 48,
            }
        }
    }

    assert _trusted_education_runtime_env(configs, kb_domain="rd") == {}
    assert _trusted_education_runtime_env({}, kb_domain="edu") == {}
    assert _trusted_education_runtime_env(configs, kb_domain="edu") == {
        "EDUCATION_RUN_GRANT": "A" * 48,
        "EDUCATION_SERVICE_URL": "http://host.docker.internal:5102",
    }


def test_education_runtime_context_rejects_malformed_or_conflicting_grants():
    malformed = {
        "_edu_1": {"education_tool_context": {"run_grant": "short"}}
    }
    conflicting = {
        "_edu_1": {"education_tool_context": {"run_grant": "A" * 48}},
        "_edu_3": {"education_tool_context": {"run_grant": "B" * 48}},
    }

    with pytest.raises(ValueError, match="invalid"):
        _trusted_education_runtime_env(malformed, kb_domain="edu")
    with pytest.raises(ValueError, match="conflicting"):
        _trusted_education_runtime_env(conflicting, kb_domain="edu")


def test_sandbox_education_action_uses_only_server_projected_scope(monkeypatch):
    requests = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit=None):
            return json.dumps(
                {
                    "call_id": "call-1",
                    "tool_name": "edu.course.context.get",
                    "replayed": False,
                    "result": {"course": {"id": "course-1"}},
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("EDUCATION_RUN_GRANT", "server-grant")
    monkeypatch.setenv(
        "EDUCATION_SERVICE_URL",
        "http://host.docker.internal:5102",
    )
    monkeypatch.setattr(container_tools.urllib.request, "urlopen", fake_urlopen)

    result = container_tools._education_action(
        action="edu.course.context.get",
        arguments={},
        idempotency_key="",
        _weagent_agent_id="_edu_1",
    )

    assert result["result"]["course"]["id"] == "course-1"
    request, timeout = requests[0]
    assert request.full_url == (
        "http://host.docker.internal:5102"
        "/api/edu/tools/edu.course.context.get/invoke"
    )
    assert request.headers["X-education-run-grant"] == "server-grant"
    payload = json.loads(request.data)
    assert payload == {
        "arguments": {},
        "idempotency_key": "",
        "agent_id": "_edu_1",
    }
    assert timeout == 30


def test_sandbox_education_action_requires_projected_grant(monkeypatch):
    monkeypatch.delenv("EDUCATION_RUN_GRANT", raising=False)

    with pytest.raises(RuntimeError, match="run grant"):
        container_tools._education_action(
            action="edu.course.context.get",
            arguments={},
        )


@pytest.fixture()
def core_app():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        agent_service.seed_default_data()
        capability_service.seed_builtin_tool_capabilities()
        capability_service.seed_education_agent_tool_bindings()
        yield app
        db.session.remove()
        db.drop_all()


def test_education_system_agents_receive_capability_bound_business_tool(core_app):
    capability = Capability.query.filter_by(
        type="tool",
        source_ref="education_actions",
        is_builtin=True,
    ).one()
    bindings = AgentCapabilityBinding.query.filter_by(
        capability_id=capability.id,
    ).all()

    assert {binding.agent_id for binding in bindings} == {
        "_edu_1",
        "_edu_2",
        "_edu_3",
        "_edu_4",
        "_edu_5",
        "_edu_6",
        "_edu_7",
        "_edu_8",
        "_edu_9",
    }
    assert all(binding.granted_permissions == ["network"] for binding in bindings)
    assert all(binding.enabled for binding in bindings)

    projection = build_capability_projection(
        "education-session",
        [{"agent_id": "_edu_1", "role": "课程设计师"}],
    )
    assert projection["agents"]["_edu_1"]["tool_index"][0]["tool_names"] == [
        "education_action"
    ]


def test_bound_education_action_records_core_capability_audit(monkeypatch, core_app):
    capability = Capability.query.filter_by(
        type="tool",
        source_ref="education_actions",
        is_builtin=True,
    ).one()
    projection = build_capability_projection(
        "education-session",
        [{"agent_id": "_edu_1", "role": "课程设计师"}],
    )
    monkeypatch.setenv("EDUCATION_RUN_GRANT", "server-grant")
    monkeypatch.setattr(
        container_tools,
        "_education_action",
        lambda **_kwargs: {"call_id": "edu-call-1", "result": {"ok": True}},
    )

    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=base) as workspace:
        write_projection(projection, workspace_root=workspace)
        write_run_snapshot(projection, "run-1", workspace_root=workspace)
        registry = container_tools.ToolRegistry(workspace_root=workspace)
        container_tools.register_builtin_tools(registry)
        registry._tools["education_action"]["fn"] = container_tools._education_action

        result = json.loads(
            registry.call_from_agent(
                "_edu_1",
                "education_action",
                {
                    "action": "edu.course.context.get",
                    "arguments": {},
                },
                run_id="run-1",
                session_id="education-session",
            )
        )

        assert result["status"] == "ok"
        calls = (
            Path(workspace)
            / ".weagent"
            / "runs"
            / "run-1"
            / "calls.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        record = json.loads(calls[0])
        assert record["capability_id"] == capability.id
        assert record["tool_name"] == "education_action"
        assert record["permissions_used"] == ["network"]
