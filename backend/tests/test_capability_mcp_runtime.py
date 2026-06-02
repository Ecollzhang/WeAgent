import json
import sys
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import AgentCapabilityBinding
from app.models.user import User
from app.sandbox.container.capabilities import write_projection, write_run_snapshot
from app.services.capability_service import capability_service


def _workspace_tempdir():
    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=base)


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _create_user_and_agent():
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
    return user, agent


def _fixture_manifest():
    return {
        "schema_version": "weagent.capability/v1",
        "source": {
            "type": "npx",
            "package": "@fixture/mcp-echo",
            "version": "1.0.0",
        },
        "capabilities": [
            {
                "type": "mcp",
                "name": "Fixture MCP Echo",
                "description": "Fixture server that echoes text",
                "permissions": {"required": ["run_command"], "optional": []},
                "entry": {"command": "npx", "args": ["-y", "@fixture/mcp-echo"]},
                "tools": [{"name": "echo", "description": "Echo input text"}],
            }
        ],
    }


def _write_fixture_mcp_server(path: Path):
    path.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            def respond(message):
                sys.stdout.write(json.dumps(message) + "\\n")
                sys.stdout.flush()

            for line in sys.stdin:
                request = json.loads(line)
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params") or {}
                if method == "initialize":
                    respond({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "serverInfo": {"name": "fixture-mcp", "version": "1.0.0"},
                        },
                    })
                elif method == "tools/list":
                    respond({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "echo",
                                    "description": "Echo input text",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {"text": {"type": "string"}},
                                        "required": ["text"],
                                    },
                                }
                            ]
                        },
                    })
                elif method == "tools/call":
                    arguments = params.get("arguments") or {}
                    respond({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {"type": "text", "text": arguments.get("text", "")}
                            ],
                            "isError": False,
                        },
                    })
                else:
                    respond({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Unknown method: {method}"},
                    })
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _mcp_projection(command: str, args: list[str], granted_permissions=None):
    granted_permissions = (
        ["run_command"] if granted_permissions is None else granted_permissions
    )
    manifest = {
        "schema_version": "weagent.capability/v1",
        "source": {
            "type": "npx",
            "package": "@fixture/mcp-echo",
            "version": "1.0.0",
        },
        "entry": {"command": command, "args": args},
        "tools": [{"name": "echo", "description": "Echo input text"}],
        "raw": {
            "type": "mcp",
            "name": "Fixture MCP Echo",
            "entry": {"command": command, "args": args},
            "tools": [{"name": "echo", "description": "Echo input text"}],
        },
    }
    return {
        "schema_version": "weagent.capability_projection/v1",
        "session_id": "session-1",
        "capabilities": {
            "mcp-1": {
                "id": "mcp-1",
                "capability_id": "mcp-1",
                "type": "mcp",
                "name": "Fixture MCP Echo",
                "source": "npx",
                "source_ref": "npx:@fixture/mcp-echo@1.0.0",
                "version": {"id": "version-1", "version": "1.0.0"},
            }
        },
        "skills": {},
        "mcp": {
            "mcp-1": {
                "runtime_id": "mcp-1",
                "capability_id": "mcp-1",
                "version_id": "version-1",
                "name": "Fixture MCP Echo",
                "description": "Fixture server that echoes text",
                "manifest": manifest,
                "permissions": {"required": ["run_command"], "optional": []},
            }
        },
        "plugins": {},
        "tools": {},
        "agents": {
            "agent-1": {
                "agent_id": "agent-1",
                "capabilities": [
                    {
                        "binding_id": "binding-1",
                        "runtime_id": "mcp-1",
                        "capability_id": "mcp-1",
                        "capability_version_id": "version-1",
                        "type": "mcp",
                        "name": "Fixture MCP Echo",
                        "source": "npx",
                        "source_ref": "npx:@fixture/mcp-echo@1.0.0",
                        "version": "1.0.0",
                        "granted_permissions": granted_permissions,
                        "manifest": manifest,
                    }
                ],
                "skill_index": [],
                "permissions": {
                    "agent_id": "agent-1",
                    "grants": [
                        {
                            "binding_id": "binding-1",
                            "capability_id": "mcp-1",
                            "capability_version_id": "version-1",
                            "capability_type": "mcp",
                            "granted_permissions": granted_permissions,
                        }
                    ],
                },
            }
        },
    }


def test_imported_npx_mcp_binding_requires_run_command(app_context):
    _user, agent = _create_user_and_agent()
    imported, error = capability_service.import_npx_manifest(
        user_id="user-1",
        manifest=_fixture_manifest(),
        source_ref="npx:@fixture/mcp-echo@1.0.0",
    )
    assert error is None
    mcp = imported[0]

    result, error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=mcp["latest_version"]["id"],
        granted_permissions=[],
    )

    assert result is None
    assert "Missing required permissions" in error
    assert AgentCapabilityBinding.query.count() == 0

    result, error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=mcp["latest_version"]["id"],
        granted_permissions=["run_command"],
    )

    assert error is None
    assert result["capability"]["type"] == "mcp"
    assert result["authorization_snapshot"]["granted_permissions"] == ["run_command"]


def test_mcp_runtime_starts_lists_calls_and_records_jsonl():
    from app.sandbox.container.mcp_runtime import McpRuntime

    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        server_path = workspace_path / "fixture_mcp_server.py"
        _write_fixture_mcp_server(server_path)
        projection = _mcp_projection(sys.executable, [str(server_path)])
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        runtime = McpRuntime(workspace_root=str(workspace_path), request_timeout=5)
        try:
            start = runtime.start_server("agent-1", "mcp-1")
            assert start["status"] == "ok"
            assert start["runtime_id"] == "mcp-1"

            tools = runtime.list_tools("mcp-1")
            assert tools["status"] == "ok"
            assert [tool["name"] for tool in tools["tools"]] == ["echo"]

            call = runtime.call_tool(
                "agent-1",
                "mcp-1",
                "echo",
                {"text": "hello mcp"},
                run_id="run-1",
                session_id="session-1",
            )

            assert call["status"] == "ok"
            assert call["result"]["content"][0]["text"] == "hello mcp"
        finally:
            runtime.stop_server("mcp-1")

        calls = (
            workspace_path / ".weagent" / "runs" / "run-1" / "calls.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        assert len(calls) == 1
        record = json.loads(calls[0])
        assert record["session_id"] == "session-1"
        assert record["run_id"] == "run-1"
        assert record["agent_id"] == "agent-1"
        assert record["capability_id"] == "mcp-1"
        assert record["capability_version_id"] == "version-1"
        assert record["call_type"] == "mcp"
        assert record["tool_name"] == "echo"
        assert record["permissions_used"] == ["run_command"]
        assert record["input_summary"] == {
            "tool_name": "echo",
            "argument_keys": ["text"],
        }
        assert record["output_summary"]["keys"] == ["content", "isError"]
        assert record["status"] == "completed"
        assert record["started_at"]
        assert record["completed_at"]


def test_mcp_runtime_refuses_start_without_run_command_grant():
    from app.sandbox.container.mcp_runtime import McpRuntime

    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        server_path = workspace_path / "fixture_mcp_server.py"
        _write_fixture_mcp_server(server_path)
        projection = _mcp_projection(
            sys.executable,
            [str(server_path)],
            granted_permissions=[],
        )
        write_projection(projection, workspace_root=str(workspace_path))

        runtime = McpRuntime(workspace_root=str(workspace_path), request_timeout=5)
        result = runtime.start_server("agent-1", "mcp-1")

        assert result["status"] == "error"
        assert "Missing granted permissions" in result["error"]
        assert runtime.list_running_servers() == []


def test_mcp_runtime_permission_failure_records_bound_capability_metadata():
    from app.sandbox.container.mcp_runtime import McpRuntime

    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        server_path = workspace_path / "fixture_mcp_server.py"
        _write_fixture_mcp_server(server_path)
        projection = _mcp_projection(
            sys.executable,
            [str(server_path)],
            granted_permissions=[],
        )
        write_projection(projection, workspace_root=str(workspace_path))
        write_run_snapshot(projection, "run-1", workspace_root=str(workspace_path))

        runtime = McpRuntime(workspace_root=str(workspace_path), request_timeout=5)
        result = runtime.call_tool(
            "agent-1",
            "mcp-1",
            "echo",
            {"text": "blocked"},
            run_id="run-1",
            session_id="session-1",
        )

        assert result["status"] == "error"
        assert "Missing granted permissions" in result["error"]

        calls = (
            workspace_path / ".weagent" / "runs" / "run-1" / "calls.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        assert len(calls) == 1
        record = json.loads(calls[0])
        assert record["capability_id"] == "mcp-1"
        assert record["capability_version_id"] == "version-1"
        assert record["status"] == "failed"
        assert record["tool_name"] == "echo"
        assert "Missing granted permissions" in record["error"]


def test_host_sandbox_api_exposes_mcp_runtime_controls(monkeypatch):
    from app.sandbox.api import routes as sandbox_routes

    app = create_app("testing")
    calls = []

    class FakeManager:
        def list_mcp_servers(self, session_id):
            calls.append(("list", session_id))
            return {"status": "ok", "servers": ["memory"]}

        def start_mcp_server(self, session_id, agent_id, runtime_id):
            calls.append(("start", session_id, agent_id, runtime_id))
            return {"status": "ok", "runtime_id": runtime_id}

        def list_mcp_tools(self, session_id, runtime_id):
            calls.append(("tools", session_id, runtime_id))
            return {"status": "ok", "tools": [{"name": "create_entities"}]}

        def call_mcp_tool(self, session_id, agent_id, runtime_id, tool_name, args):
            calls.append(("call", session_id, agent_id, runtime_id, tool_name, args))
            return {"status": "ok", "result": {"content": [{"type": "text", "text": "ok"}]}}

        def stop_mcp_server(self, session_id, runtime_id):
            calls.append(("stop", session_id, runtime_id))
            return {"status": "ok", "stopped": True}

    monkeypatch.setattr(sandbox_routes, "_mgr", lambda: FakeManager())
    client = app.test_client()

    assert client.get("/api/sandbox/sessions/session-1/mcp/servers").status_code == 200
    assert client.post(
        "/api/sandbox/sessions/session-1/mcp/memory/start",
        json={"agent_id": "agent-1"},
    ).status_code == 200
    assert client.get("/api/sandbox/sessions/session-1/mcp/memory/tools").status_code == 200
    assert client.post(
        "/api/sandbox/sessions/session-1/mcp/memory/call",
        json={"agent_id": "agent-1", "tool_name": "create_entities", "args": {"entities": []}},
    ).status_code == 200
    assert client.post("/api/sandbox/sessions/session-1/mcp/memory/stop").status_code == 200

    assert calls == [
        ("list", "session-1"),
        ("start", "session-1", "agent-1", "memory"),
        ("tools", "session-1", "memory"),
        ("call", "session-1", "agent-1", "memory", "create_entities", {"entities": []}),
        ("stop", "session-1", "memory"),
    ]
