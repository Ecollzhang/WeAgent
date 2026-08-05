from types import SimpleNamespace

from app.sandbox.host.manager import DockerContainerManager


class PreflightClient:
    def __init__(self):
        self.calls = []

    def preflight_agent_tools(self, agent_id, required_tools):
        self.calls.append((agent_id, tuple(required_tools)))
        return {
            "agent_id": agent_id,
            "ready": True,
            "available_tools": list(required_tools),
            "missing_tools": [],
        }


def test_tool_preflight_can_scope_workers_without_requiring_moderator_tools():
    manager = DockerContainerManager()
    client = PreflightClient()
    manager._sessions["conversation-1"] = SimpleNamespace(
        agents_config=[
            {"agent_id": "_edu_1"},
            {"agent_id": "_edu_2"},
            {"agent_id": "_edu_9"},
            {"agent_id": "moderator"},
        ],
        client=client,
    )

    result = manager.preflight_tools(
        "conversation-1",
        ["education_action"],
        agent_ids=["_edu_1", "_edu_2", "_edu_9"],
    )

    assert result["ready"] is True
    assert [call[0] for call in client.calls] == ["_edu_1", "_edu_2", "_edu_9"]
    assert result["checked_agent_ids"] == ["_edu_1", "_edu_2", "_edu_9"]


def test_tool_preflight_rejects_unknown_requested_agent():
    manager = DockerContainerManager()
    client = PreflightClient()
    manager._sessions["conversation-1"] = SimpleNamespace(
        agents_config=[{"agent_id": "_edu_1"}],
        client=client,
    )

    result = manager.preflight_tools(
        "conversation-1",
        ["education_action"],
        agent_ids=["_edu_1", "invented-agent"],
    )

    assert result["ready"] is False
    assert result["missing_agent_ids"] == ["invented-agent"]
    assert [call[0] for call in client.calls] == ["_edu_1"]
