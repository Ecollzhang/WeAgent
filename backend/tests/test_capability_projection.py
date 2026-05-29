import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import AgentCapabilityBinding
from app.models.user import User
from app.services.capability_service import capability_service
from app.services.capability_projection_service import build_capability_projection


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _create_user_and_agents():
    user = User(
        id="user-1",
        username="toolset-user",
        email="toolset@example.com",
        password_hash="hash",
    )
    agent_a = Agent(
        id="agent-a",
        name="Reviewer",
        agent_type="custom",
        adapter_name="claude",
        user_id=user.id,
        created_by=user.id,
    )
    agent_b = Agent(
        id="agent-b",
        name="Builder",
        agent_type="custom",
        adapter_name="claude",
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add_all([user, agent_a, agent_b])
    db.session.commit()
    return user, agent_a, agent_b


def test_projection_uses_pinned_enabled_bindings_and_agent_scoped_views(app_context):
    _user, agent_a, agent_b = _create_user_and_agents()
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Review Skill",
        markdown="# Review Skill\nUse the v1 checklist.",
        permissions={"required": ["read_workspace"], "optional": ["write_workspace"]},
    )
    assert error is None
    pinned_version_id = skill["latest_version"]["id"]

    newer, error = capability_service.create_version(
        capability_id=skill["id"],
        content="# Review Skill\nUse the v2 checklist.",
        permissions={"required": ["read_workspace"], "optional": ["write_workspace"]},
    )
    assert error is None
    assert newer["id"] != pinned_version_id

    for agent in (agent_a, agent_b):
        result, error = capability_service.bind_to_agent(
            agent_id=agent.id,
            capability_version_id=pinned_version_id,
            granted_permissions=["read_workspace"],
        )
        assert error is None
        assert result["version_policy"] == "pinned"

    disabled_skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Disabled Skill",
        markdown="# Disabled Skill",
    )
    assert error is None
    result, error = capability_service.bind_to_agent(
        agent_id=agent_a.id,
        capability_version_id=disabled_skill["latest_version"]["id"],
        granted_permissions=[],
        enabled=False,
    )
    assert error is None

    projection = build_capability_projection(
        session_id="session-1",
        agents=[
            {"agent_id": agent_a.id, "role": agent_a.name},
            {"agent_id": agent_b.id, "role": agent_b.name},
        ],
    )

    assert projection["schema_version"] == "weagent.capability_projection/v1"
    assert projection["session_id"] == "session-1"
    assert list(projection["capabilities"].keys()) == [skill["id"]]
    assert projection["capabilities"][skill["id"]]["version"]["id"] == pinned_version_id
    assert "v1 checklist" in projection["skills"][skill["id"]]["content"]
    assert "v2 checklist" not in projection["skills"][skill["id"]]["content"]
    assert disabled_skill["id"] not in projection["capabilities"]

    agent_a_view = projection["agents"][agent_a.id]
    agent_b_view = projection["agents"][agent_b.id]
    assert agent_a_view["skill_index"][0]["path"] == (
        f"/workspace/.weagent/skills/{skill['id']}/SKILL.md"
    )
    assert agent_b_view["skill_index"][0]["capability_id"] == skill["id"]
    assert agent_a_view["permissions"]["grants"][0]["granted_permissions"] == ["read_workspace"]
    assert agent_a_view["permissions"]["grants"][0]["authorization_snapshot"][
        "capability_version_id"
    ] == pinned_version_id
    assert ".weagent/agents/agent-a/skill-index.json" in agent_a_view["bootstrap"]
    assert ".claude" not in agent_a_view["bootstrap"]
    assert ".codex" not in agent_a_view["bootstrap"]
    assert ".mcp.json" not in agent_a_view["bootstrap"]


def test_projection_separates_same_skill_when_agents_pin_different_versions(app_context):
    _user, agent_a, agent_b = _create_user_and_agents()
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Version Split Skill",
        markdown="# Version Split Skill\nv1 rules",
    )
    assert error is None
    v1_id = skill["latest_version"]["id"]
    v2, error = capability_service.create_version(
        capability_id=skill["id"],
        content="# Version Split Skill\nv2 rules",
        permissions={"required": [], "optional": []},
    )
    assert error is None

    capability_service.bind_to_agent(
        agent_id=agent_a.id,
        capability_version_id=v1_id,
        granted_permissions=[],
    )
    capability_service.bind_to_agent(
        agent_id=agent_b.id,
        capability_version_id=v2["id"],
        granted_permissions=[],
    )

    projection = build_capability_projection(
        session_id="session-1",
        agents=[
            {"agent_id": agent_a.id, "role": agent_a.name},
            {"agent_id": agent_b.id, "role": agent_b.name},
        ],
    )

    assert len(projection["skills"]) == 2
    agent_a_skill = projection["agents"][agent_a.id]["skill_index"][0]
    agent_b_skill = projection["agents"][agent_b.id]["skill_index"][0]
    assert agent_a_skill["version_id"] == v1_id
    assert agent_b_skill["version_id"] == v2["id"]
    assert agent_a_skill["path"] != agent_b_skill["path"]
    assert "v1 rules" in projection["skills"][agent_a_skill["runtime_id"]]["content"]
    assert "v2 rules" in projection["skills"][agent_b_skill["runtime_id"]]["content"]


def test_projection_keeps_skill_mcp_plugin_and_tool_as_peer_types(app_context):
    _user, agent_a, _agent_b = _create_user_and_agents()
    imported, error = capability_service.import_npx_manifest(
        user_id="user-1",
        source_ref="npx:@example/toolset@1.0.0",
        manifest={
            "schema_version": "weagent.capability/v1",
            "source": {
                "type": "npx",
                "package": "@example/toolset",
                "version": "1.0.0",
            },
            "capabilities": [
                {
                    "type": "mcp",
                    "name": "Example MCP",
                    "permissions": {"required": ["run_command"], "optional": ["network"]},
                    "entry": {"command": "npx", "args": ["-y", "@example/toolset"]},
                    "tools": [{"name": "echo"}],
                },
                {
                    "type": "plugin",
                    "name": "Example Plugin",
                    "permissions": {"required": [], "optional": []},
                    "entry": {"module": "@example/toolset/plugin"},
                },
            ],
        },
    )
    assert error is None
    mcp = next(item for item in imported if item["type"] == "mcp")
    plugin = next(item for item in imported if item["type"] == "plugin")
    tool = capability_service.seed_builtin_tool_capabilities()
    assert tool is None
    builtin = next(
        cap for cap in capability_service.list_capabilities("user-1", "tool")[0]
        if cap["source_ref"] == "web_search"
    )

    capability_service.bind_to_agent(
        agent_id=agent_a.id,
        capability_version_id=mcp["latest_version"]["id"],
        granted_permissions=["run_command"],
    )
    capability_service.bind_to_agent(
        agent_id=agent_a.id,
        capability_version_id=plugin["latest_version"]["id"],
        granted_permissions=[],
    )
    capability_service.bind_to_agent(
        agent_id=agent_a.id,
        capability_version_id=builtin["latest_version"]["id"],
        granted_permissions=["network"],
    )

    projection = build_capability_projection(
        session_id="session-1",
        agents=[{"agent_id": agent_a.id, "role": agent_a.name}],
    )

    assert set(projection["mcp"].keys()) == {mcp["id"]}
    assert set(projection["plugins"].keys()) == {plugin["id"]}
    assert set(projection["tools"].keys()) == {builtin["id"]}
    assert projection["mcp"][mcp["id"]]["manifest"]["raw"]["tools"] == [{"name": "echo"}]
    assert projection["plugins"][plugin["id"]]["path"] == (
        f"/workspace/.weagent/plugins/{plugin['id']}/manifest.json"
    )
    assert AgentCapabilityBinding.query.filter_by(agent_id=agent_a.id).count() == 3
