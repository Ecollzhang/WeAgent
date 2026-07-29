import importlib.machinery
import importlib.util
import json
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def load_script_module(name):
    path = BACKEND_ROOT / "app/sandbox/bin/weagent-tools-mcp"
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def projection(tmp_path):
    agent_dir = tmp_path / ".weagent" / "agents" / "agent-1"
    agent_dir.mkdir(parents=True)
    (agent_dir / "capabilities.json").write_text(
        json.dumps(
            {
                "capabilities": [
                    {
                        "type": "tool",
                        "name": "Education actions",
                        "description": "Scoped Education business operations",
                        "tool_names": ["education_action"],
                        "status": "implemented",
                        "manifest": {
                            "input_schema": {
                                "type": "object",
                                "required": ["action", "arguments"],
                                "properties": {
                                    "action": {"type": "string"},
                                    "arguments": {"type": "object"},
                                },
                                "additionalProperties": False,
                            }
                        },
                    },
                    {
                        "type": "tool",
                        "name": "Deferred tool",
                        "tool_names": ["not_available"],
                        "status": "deferred",
                        "manifest": {"input_schema": {"type": "object"}},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_lists_only_executable_tools_with_projected_schema(tmp_path):
    module = load_script_module("weagent_tools_mcp_list")
    projection(tmp_path)

    tools = module.load_bound_tools("agent-1", str(tmp_path))

    assert list(tools) == ["education_action"]
    assert tools["education_action"]["inputSchema"]["required"] == [
        "action",
        "arguments",
    ]
    assert tools["education_action"]["description"] == (
        "Scoped Education business operations"
    )


def test_mcp_call_uses_local_orchestrator_and_preserves_error_envelope(
    tmp_path,
    monkeypatch,
):
    module = load_script_module("weagent_tools_mcp_call")
    projection(tmp_path)
    requests = []

    def fake_request(payload):
        requests.append(payload)
        return {
            "status": "ok",
            "result": {
                "status": "error",
                "error": "lesson_not_found: lesson not found",
            },
        }

    monkeypatch.setattr(module, "request_tool", fake_request)
    response = module.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "education_action",
                "arguments": {
                    "action": "edu.course.context.get",
                    "arguments": {},
                },
            },
        },
        agent_id="agent-1",
        workspace_root=str(tmp_path),
    )

    assert requests == [
        {
            "agent_id": "agent-1",
            "tool_name": "education_action",
            "args": {
                "action": "edu.course.context.get",
                "arguments": {},
            },
        }
    ]
    result = response["result"]
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["error"].startswith(
        "lesson_not_found"
    )


def test_mcp_rejects_unbound_tool_without_calling_orchestrator(
    tmp_path,
    monkeypatch,
):
    module = load_script_module("weagent_tools_mcp_unbound")
    projection(tmp_path)
    monkeypatch.setattr(
        module,
        "request_tool",
        lambda _payload: (_ for _ in ()).throw(AssertionError("must not call")),
    )

    response = module.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "run_command", "arguments": {}},
        },
        agent_id="agent-1",
        workspace_root=str(tmp_path),
    )

    assert response["error"]["code"] == -32602
    assert "not bound" in response["error"]["message"]
