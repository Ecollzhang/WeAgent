import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import (
    AgentCapabilityBinding,
    Capability,
    CapabilityVersion,
    PluginInstallRecord,
)
from app.models.user import User
from app.services.capability_service import REQUIRED_PERMISSIONS, capability_service


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_user(user_id="user-1"):
    user = User(
        id=user_id,
        username=f"{user_id}-name",
        email=f"{user_id}@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_agent(user_id="user-1"):
    agent = Agent(
        id="agent-1",
        name="Reviewer",
        agent_type="custom",
        adapter_name="claude",
        user_id=user_id,
        created_by=user_id,
    )
    db.session.add(agent)
    db.session.commit()
    return agent


def test_create_skill_creates_capability_and_initial_version(app_context):
    create_user()

    result, error = capability_service.create_skill(
        user_id="user-1",
        name="Code Review",
        markdown="# Code Review\nFind bugs first.",
        description="Review code changes",
        meta={"format": "markdown"},
    )

    assert error is None
    assert result["type"] == "skill"
    assert result["latest_version"]["version"] == "1.0.0"
    assert result["latest_version"]["content"].startswith("# Code Review")
    assert Capability.query.count() == 1
    assert CapabilityVersion.query.count() == 1


def test_bind_to_agent_requires_declared_required_permissions(app_context):
    create_user()
    agent = create_agent()
    skill_result, _ = capability_service.create_skill(
        user_id="user-1",
        name="Workspace Writer",
        markdown="# Writer",
        permissions={"required": ["write_workspace"], "optional": ["read_workspace"]},
    )
    version_id = skill_result["latest_version"]["id"]

    result, error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=version_id,
        granted_permissions=["read_workspace"],
    )

    assert result is None
    assert "Missing required permissions" in error
    assert AgentCapabilityBinding.query.count() == 0


def test_bind_to_agent_pins_version_and_snapshot(app_context):
    create_user()
    agent = create_agent()
    skill_result, _ = capability_service.create_skill(
        user_id="user-1",
        name="Workspace Reader",
        markdown="# Reader",
        permissions={"required": ["read_workspace"], "optional": []},
    )

    result, error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=skill_result["latest_version"]["id"],
        granted_permissions=["read_workspace"],
    )

    assert error is None
    assert result["version_policy"] == "pinned"
    assert result["granted_permissions"] == ["read_workspace"]
    assert result["authorization_snapshot"]["declared_permissions"]["required"] == ["read_workspace"]
    assert AgentCapabilityBinding.query.one().capability_version.version == "1.0.0"


def test_upgrade_status_reports_newer_version_without_changing_binding(app_context):
    create_user()
    agent = create_agent()
    skill_result, _ = capability_service.create_skill(
        user_id="user-1",
        name="Planner",
        markdown="# Planner v1",
    )
    capability_id = skill_result["id"]
    first_version_id = skill_result["latest_version"]["id"]
    bind_result, bind_error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=first_version_id,
        granted_permissions=[],
    )
    assert bind_error is None

    new_version, error = capability_service.create_version(
        capability_id=capability_id,
        content="# Planner v2",
        permissions={"required": [], "optional": []},
    )
    assert error is None

    upgrades, error = capability_service.get_upgrade_status(agent.id)

    assert error is None
    assert upgrades == [
        {
            "binding_id": bind_result["id"],
            "capability_id": capability_id,
            "current_version_id": first_version_id,
            "latest_version_id": new_version["id"],
            "upgrade_available": True,
        }
    ]
    assert AgentCapabilityBinding.query.one().capability_version_id == first_version_id


def test_import_npx_manifest_creates_mcp_and_plugin_capabilities(app_context):
    create_user()
    manifest = {
        "schema_version": "weagent.capability/v1",
        "source": {"type": "npx", "package": "@example/mcp", "version": "1.0.0"},
        "capabilities": [
            {
                "type": "mcp",
                "name": "Example MCP",
                "description": "Example server",
                "permissions": {"required": ["run_command"], "optional": ["network"]},
                "entry": {"command": "npx", "args": ["-y", "@example/mcp"]},
                "tools": [{"name": "echo", "description": "Echo input"}],
            },
            {
                "type": "plugin",
                "name": "Example Plugin",
                "description": "Plugin wrapper",
                "permissions": {"required": [], "optional": []},
            },
        ],
    }

    result, error = capability_service.import_npx_manifest(
        user_id="user-1",
        manifest=manifest,
        source_ref="npx:@example/mcp@1.0.0",
    )

    assert error is None
    assert {item["type"] for item in result} == {"mcp", "plugin"}
    assert Capability.query.filter_by(type="mcp").one().source == "npx"
    assert REQUIRED_PERMISSIONS.issuperset({"run_command", "network"})


def test_import_plugin_manifest_creates_install_record(app_context):
    create_user()
    manifest = {
        "schema_version": "weagent.capability/v1",
        "source": {"type": "npx", "package": "@example/plugin", "version": "2.1.0"},
        "capabilities": [
            {
                "type": "plugin",
                "name": "Example Plugin",
                "description": "Plugin wrapper",
                "permissions": {"required": [], "optional": []},
                "entry": {"module": "@example/plugin"},
                "included_capabilities": [
                    {"type": "skill", "name": "Plugin Skill"},
                    {"type": "mcp", "name": "Plugin MCP"},
                ],
            },
        ],
    }

    result, error = capability_service.import_npx_manifest(
        user_id="user-1",
        manifest=manifest,
        source_ref="npx:@example/plugin@2.1.0",
    )

    assert error is None
    plugin = result[0]
    assert plugin["type"] == "plugin"
    assert plugin["install_record"]["status"] == "installed"
    assert plugin["install_record"]["source"] == "npx"
    assert plugin["install_record"]["source_ref"] == "npx:@example/plugin@2.1.0"
    assert plugin["install_record"]["package_name"] == "@example/plugin"
    assert plugin["install_record"]["package_version"] == "2.1.0"
    assert plugin["install_record"]["included_capabilities"] == [
        {"type": "skill", "name": "Plugin Skill"},
        {"type": "mcp", "name": "Plugin MCP"},
    ]
    assert PluginInstallRecord.query.count() == 1
