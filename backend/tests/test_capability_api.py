import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import SkillRevisionDraft
from app.models.user import User
from app.services.capability_service import capability_service


@pytest.fixture()
def client_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
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
        token = create_access_token(identity=user.id)
        yield app.test_client(), {"Authorization": f"Bearer {token}"}, user, agent
        db.session.remove()
        db.drop_all()


def test_create_and_list_skill_capability(client_context):
    client, headers, _user, _agent = client_context

    create_response = client.post(
        "/api/capabilities/skills",
        headers=headers,
        json={
            "name": "Code Review",
            "markdown": "# Code Review\nFind bugs first.",
            "description": "Review code",
            "permissions": {"required": ["read_workspace"], "optional": []},
        },
    )

    assert create_response.status_code == 201
    created = create_response.get_json()["data"]
    assert created["type"] == "skill"
    assert created["latest_version"]["permissions"]["required"] == ["read_workspace"]

    list_response = client.get("/api/capabilities?type=skill", headers=headers)

    assert list_response.status_code == 200
    items = list_response.get_json()["data"]
    assert [item["name"] for item in items] == ["Code Review"]


def test_import_npx_manifest_and_bind_agent_capability(client_context):
    client, headers, _user, agent = client_context

    import_response = client.post(
        "/api/capabilities/import/npx-manifest",
        headers=headers,
        json={
            "source_ref": "npx:@example/mcp@1.0.0",
            "manifest": {
                "schema_version": "weagent.capability/v1",
                "source": {"type": "npx", "package": "@example/mcp", "version": "1.0.0"},
                "capabilities": [
                    {
                        "type": "mcp",
                        "name": "Example MCP",
                        "permissions": {
                            "required": ["run_command"],
                            "optional": ["network"],
                        },
                        "entry": {"command": "npx", "args": ["-y", "@example/mcp"]},
                        "tools": [{"name": "echo"}],
                    }
                ],
            },
        },
    )

    assert import_response.status_code == 201
    version_id = import_response.get_json()["data"][0]["latest_version"]["id"]

    rejected = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={"capability_version_id": version_id, "granted_permissions": []},
    )
    assert rejected.status_code == 400
    assert "Missing required permissions" in rejected.get_json()["message"]

    accepted = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": version_id,
            "granted_permissions": ["run_command"],
        },
    )

    assert accepted.status_code == 201
    binding = accepted.get_json()["data"]
    assert binding["agent_id"] == agent.id
    assert binding["authorization_snapshot"]["granted_permissions"] == ["run_command"]

    list_response = client.get(f"/api/agents/{agent.id}/capabilities", headers=headers)

    assert list_response.status_code == 200
    assert list_response.get_json()["data"][0]["capability"]["type"] == "mcp"


def test_create_agent_can_persist_default_capability_bindings(client_context):
    client, headers, _user, _agent = client_context
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Default Reviewer",
        markdown="# Default Reviewer",
    )
    assert error is None

    create_response = client.post(
        "/api/agents",
        headers=headers,
        json={
            "name": "Bound Agent",
            "adapter_name": "claude",
            "capability_bindings": [
                {
                    "capability_version_id": skill["latest_version"]["id"],
                    "granted_permissions": [],
                }
            ],
        },
    )

    assert create_response.status_code == 201
    created_agent_id = create_response.get_json()["data"]["id"]

    bindings_response = client.get(
        f"/api/agents/{created_agent_id}/capabilities",
        headers=headers,
    )
    assert bindings_response.status_code == 200
    assert bindings_response.get_json()["data"][0]["capability"]["name"] == "Default Reviewer"


def test_agent_binding_rejects_other_users_capability(client_context):
    client, headers, _user, agent = client_context
    other_user = User(
        id="user-2",
        username="other-user",
        email="other@example.com",
        password_hash="hash",
    )
    db.session.add(other_user)
    db.session.commit()
    skill, error = capability_service.create_skill(
        user_id="user-2",
        name="Private Skill",
        markdown="# Private Skill",
    )
    assert error is None

    response = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": skill["latest_version"]["id"],
            "granted_permissions": [],
        },
    )

    assert response.status_code == 400
    assert "Capability version not found" in response.get_json()["message"]


def test_draft_publish_fork_and_call_record_sync(client_context):
    client, headers, _user, agent = client_context
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Runtime Skill",
        markdown="# Runtime Skill\nOriginal.",
    )
    assert error is None
    draft = SkillRevisionDraft(
        source_skill_id=skill["id"],
        source_version_id=skill["latest_version"]["id"],
        session_id="session-1",
        agent_id=agent.id,
        diff={"changed": ["SKILL.md"]},
        full_markdown="# Runtime Skill\nUpdated by agent.",
    )
    fork_draft = SkillRevisionDraft(
        source_skill_id=skill["id"],
        source_version_id=skill["latest_version"]["id"],
        session_id="session-1",
        agent_id=agent.id,
        diff={"changed": ["SKILL.md"]},
        full_markdown="# Forked Skill\nA safer variant.",
    )
    db.session.add_all([draft, fork_draft])
    db.session.commit()

    drafts_response = client.get("/api/capabilities/drafts", headers=headers)
    assert drafts_response.status_code == 200
    assert len(drafts_response.get_json()["data"]) == 2

    publish_response = client.post(
        f"/api/capabilities/drafts/{draft.id}/publish",
        headers=headers,
        json={"version": "1.0.1"},
    )
    assert publish_response.status_code == 200
    assert publish_response.get_json()["data"]["draft"]["status"] == "published"

    fork_response = client.post(
        f"/api/capabilities/drafts/{fork_draft.id}/fork",
        headers=headers,
        json={"name": "Forked Skill"},
    )
    assert fork_response.status_code == 201
    assert fork_response.get_json()["data"]["capability"]["name"] == "Forked Skill"

    sync_response = client.post(
        "/api/capabilities/calls/sync",
        headers=headers,
        json={
            "records": [
                {
                    "session_id": "session-1",
                    "run_id": "run-1",
                    "agent_id": agent.id,
                    "capability_id": skill["id"],
                    "capability_version_id": skill["latest_version"]["id"],
                    "call_type": "tool",
                    "tool_name": "read_file",
                    "permissions_used": ["read_workspace"],
                    "input_summary": {"path": "README.md"},
                    "output_summary": {"bytes": 10},
                    "status": "completed",
                }
            ]
        },
    )
    assert sync_response.status_code == 201

    calls_response = client.get(
        "/api/capabilities/calls?session_id=session-1",
        headers=headers,
    )
    assert calls_response.status_code == 200
    assert calls_response.get_json()["data"][0]["tool_name"] == "read_file"
