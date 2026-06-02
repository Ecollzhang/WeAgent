import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import CapabilityCallRecord
from app.models.user import User
from app.sandbox.container import tools as container_tools
from app.sandbox.container.capabilities import write_projection, write_run_snapshot
from app.services.capability_call_sync_service import capability_call_sync_service
from app.services.capability_service import capability_service


def _workspace_tempdir():
    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=base)


def _tool_projection():
    return {
        "schema_version": "weagent.capability_projection/v1",
        "session_id": "session-1",
        "capabilities": {
            "tool-1": {
                "id": "tool-1",
                "capability_id": "tool-1",
                "type": "tool",
                "name": "File Operations",
                "source": "builtin",
                "source_ref": "file_operations",
                "version": {"id": "version-1", "version": "1.0.0"},
            }
        },
        "skills": {},
        "mcp": {},
        "plugins": {},
        "tools": {
            "tool-1": {
                "runtime_id": "tool-1",
                "capability_id": "tool-1",
                "version_id": "version-1",
                "name": "File Operations",
                "source": "builtin",
                "source_ref": "file_operations",
                "manifest": {"tool": {"value": "file_operations"}, "runtime": "builtin"},
                "permissions": {
                    "required": ["read_workspace"],
                    "optional": ["write_workspace"],
                },
            }
        },
        "agents": {
            "agent-1": {
                "agent_id": "agent-1",
                "capabilities": [
                    {
                        "binding_id": "binding-1",
                        "runtime_id": "tool-1",
                        "capability_id": "tool-1",
                        "capability_version_id": "version-1",
                        "type": "tool",
                        "name": "File Operations",
                        "source": "builtin",
                        "source_ref": "file_operations",
                        "version": "1.0.0",
                        "granted_permissions": ["read_workspace"],
                        "manifest": {
                            "tool": {"value": "file_operations"},
                            "runtime": "builtin",
                        },
                    }
                ],
                "skill_index": [],
                "permissions": {
                    "agent_id": "agent-1",
                    "grants": [
                        {
                            "binding_id": "binding-1",
                            "capability_id": "tool-1",
                            "capability_version_id": "version-1",
                            "capability_type": "tool",
                            "granted_permissions": ["read_workspace"],
                        }
                    ],
                },
            }
        },
    }


def test_bound_builtin_tool_call_writes_completed_jsonl_record():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        (workspace_path / "sample.txt").write_text("hello audit", encoding="utf-8")
        projection = _tool_projection()
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        registry = container_tools.ToolRegistry(workspace_root=str(workspace_path))
        container_tools.register_builtin_tools(registry)

        result = json.loads(
            registry.call_from_agent(
                "agent-1",
                "read_file",
                {"path": "sample.txt"},
                run_id="run-1",
                session_id="session-1",
            )
        )

        assert result["status"] == "ok"
        assert result["result"] == "hello audit"

        calls = (workspace_path / ".weagent" / "runs" / "run-1" / "calls.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(calls) == 1
        record = json.loads(calls[0])
        assert record["session_id"] == "session-1"
        assert record["run_id"] == "run-1"
        assert record["agent_id"] == "agent-1"
        assert record["capability_id"] == "tool-1"
        assert record["capability_version_id"] == "version-1"
        assert record["call_type"] == "tool"
        assert record["tool_name"] == "read_file"
        assert record["permissions_used"] == ["read_workspace"]
        assert record["input_summary"] == {"path": "sample.txt"}
        assert record["output_summary"]["text_length"] == len("hello audit")
        assert record["status"] == "completed"
        assert record["started_at"]
        assert record["completed_at"]


def test_bound_builtin_tool_call_records_permission_failure():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        projection = _tool_projection()
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        registry = container_tools.ToolRegistry(workspace_root=str(workspace_path))
        container_tools.register_builtin_tools(registry)

        result = json.loads(
            registry.call_from_agent(
                "agent-1",
                "write_file",
                {"path": "sample.txt", "content": "blocked"},
                run_id="run-1",
                session_id="session-1",
            )
        )

        assert result["status"] == "error"
        assert "Missing granted permissions" in result["error"]
        assert not (workspace_path / "sample.txt").exists()

        calls = (workspace_path / ".weagent" / "runs" / "run-1" / "calls.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(calls) == 1
        record = json.loads(calls[0])
        assert record["tool_name"] == "write_file"
        assert record["permissions_used"] == ["write_workspace"]
        assert record["status"] == "failed"
        assert "Missing granted permissions" in record["error"]


def test_capability_aware_session_rejects_unbound_tool_call():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        (workspace_path / "sample.txt").write_text("hello audit", encoding="utf-8")
        projection = _tool_projection()
        projection["agents"]["agent-1"]["capabilities"] = []
        projection["agents"]["agent-1"]["permissions"]["grants"] = []
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        registry = container_tools.ToolRegistry(workspace_root=str(workspace_path))
        container_tools.register_builtin_tools(registry)

        result = json.loads(
            registry.call_from_agent(
                "agent-1",
                "read_file",
                {"path": "sample.txt"},
                run_id="run-1",
                session_id="session-1",
            )
        )

        assert result["status"] == "error"
        assert "not bound" in result["error"]


def test_deferred_builtin_tool_binding_is_not_executable():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        projection = _tool_projection()
        projection["capabilities"]["tool-1"]["source_ref"] = "code_generator"
        projection["tools"]["tool-1"]["source_ref"] = "code_generator"
        projection["tools"]["tool-1"]["manifest"] = {
            "schema_version": "weagent.tool/v1",
            "runtime": "builtin",
            "handler": "code.generate",
            "tool_names": ["code_generator"],
            "ui": {"status": "deferred"},
        }
        projection["agents"]["agent-1"]["capabilities"][0]["source_ref"] = "code_generator"
        projection["agents"]["agent-1"]["capabilities"][0]["manifest"] = (
            projection["tools"]["tool-1"]["manifest"]
        )
        projection["agents"]["agent-1"]["capabilities"][0]["granted_permissions"] = []
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        registry = container_tools.ToolRegistry(workspace_root=str(workspace_path))
        container_tools.register_builtin_tools(registry)

        result = json.loads(
            registry.call_from_agent(
                "agent-1",
                "code_generator",
                {},
                run_id="run-1",
                session_id="session-1",
            )
        )

        assert result["status"] == "error"
        assert "not executable" in result["error"]

        calls = (workspace_path / ".weagent" / "runs" / "run-1" / "calls.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(calls) == 1
        record = json.loads(calls[0])
        assert record["tool_name"] == "code_generator"
        assert record["status"] == "failed"
        assert "not executable" in record["error"]


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_jsonl_call_sync_service_persists_capability_call_records(app_context):
    user = User(
        id="user-1",
        username="toolset-user",
        email="toolset@example.com",
        password_hash="hash",
    )
    agent = Agent(
        id="agent-1",
        name="Reviewer",
        agent_type="custom",
        adapter_name="claude",
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add_all([user, agent])
    db.session.commit()
    capability_service.seed_builtin_tool_capabilities()
    tool = next(
        item for item in capability_service.list_capabilities(user.id, "tool")[0]
        if item["source_ref"] == "file_operations"
    )

    jsonl = json.dumps(
        {
            "session_id": "session-1",
            "run_id": "run-1",
            "agent_id": agent.id,
            "capability_id": tool["id"],
            "capability_version_id": tool["latest_version"]["id"],
            "call_type": "tool",
            "tool_name": "read_file",
            "permissions_used": ["read_workspace"],
            "input_summary": {"path": "sample.txt"},
            "output_summary": {"text_length": 11},
            "status": "completed",
            "started_at": "2026-05-29T10:00:00",
            "completed_at": "2026-05-29T10:00:01",
        },
        ensure_ascii=False,
    )

    result, error = capability_call_sync_service.sync_jsonl(user.id, jsonl)

    assert error is None
    assert len(result) == 1
    saved = CapabilityCallRecord.query.one()
    assert saved.session_id == "session-1"
    assert saved.run_id == "run-1"
    assert saved.agent_id == agent.id
    assert saved.capability_id == tool["id"]
    assert saved.tool_name == "read_file"
    assert saved.status == "completed"
