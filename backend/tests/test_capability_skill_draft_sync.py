import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import AgentCapabilityBinding, SkillRevisionDraft
from app.models.conversation import Conversation
from app.models.user import User
from app.sandbox.container.capabilities import (
    collect_skill_draft_payloads,
    write_projection,
)
from app.sandbox.host.manager import DockerContainerManager
from app.services.capability_draft_sync_service import capability_draft_sync_service
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


@pytest.fixture()
def client_context():
    from flask_jwt_extended import create_access_token

    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        user, agent = _create_user_and_agent()
        token = create_access_token(identity=user.id)
        yield app.test_client(), {"Authorization": f"Bearer {token}"}, user, agent
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


def _skill_projection():
    return {
        "schema_version": "weagent.capability_projection/v1",
        "session_id": "session-1",
        "capabilities": {
            "skill-1": {
                "id": "skill-1",
                "capability_id": "skill-1",
                "type": "skill",
                "name": "Runtime Skill",
                "version": {"id": "version-1", "version": "1.0.0"},
            }
        },
        "skills": {
            "skill-1": {
                "runtime_id": "skill-1",
                "capability_id": "skill-1",
                "version_id": "version-1",
                "name": "Runtime Skill",
                "description": "Editable runtime skill",
                "content": "# Runtime Skill\nOriginal instructions.",
                "manifest": {"entry": "SKILL.md", "format": "markdown"},
                "permissions": {"required": [], "optional": ["modify_skill"]},
            }
        },
        "mcp": {},
        "plugins": {},
        "tools": {},
        "agents": {
            "agent-1": {
                "agent_id": "agent-1",
                "capabilities": [
                    {
                        "binding_id": "binding-1",
                        "runtime_id": "skill-1",
                        "capability_id": "skill-1",
                        "capability_version_id": "version-1",
                        "type": "skill",
                        "name": "Runtime Skill",
                        "version": "1.0.0",
                        "granted_permissions": ["modify_skill"],
                    }
                ],
                "skill_index": [
                    {
                        "runtime_id": "skill-1",
                        "capability_id": "skill-1",
                        "version_id": "version-1",
                        "name": "Runtime Skill",
                        "path": "/workspace/.weagent/skills/skill-1/SKILL.md",
                    }
                ],
                "permissions": {
                    "agent_id": "agent-1",
                    "grants": [
                        {
                            "binding_id": "binding-1",
                            "capability_id": "skill-1",
                            "capability_version_id": "version-1",
                            "capability_type": "skill",
                            "granted_permissions": ["modify_skill"],
                        }
                    ],
                },
            }
        },
    }


def test_runtime_skill_change_collects_draft_payload_once():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        projection = _skill_projection()
        write_projection(projection, workspace_root=str(workspace_path))

        assert collect_skill_draft_payloads(
            "agent-1",
            "session-1",
            workspace_root=str(workspace_path),
        ) == []

        skill_path = workspace_path / ".weagent" / "skills" / "skill-1" / "SKILL.md"
        skill_path.write_text(
            "# Runtime Skill\nUpdated by the agent.",
            encoding="utf-8",
        )

        drafts = collect_skill_draft_payloads(
            "agent-1",
            "session-1",
            workspace_root=str(workspace_path),
        )

        assert len(drafts) == 1
        draft = drafts[0]
        assert draft["session_id"] == "session-1"
        assert draft["agent_id"] == "agent-1"
        assert draft["source_skill_id"] == "skill-1"
        assert draft["source_version_id"] == "version-1"
        assert draft["runtime_id"] == "skill-1"
        assert draft["full_markdown"].endswith("Updated by the agent.")
        assert draft["diff"]["changed"] == ["SKILL.md"]
        assert draft["diff"]["old_checksum"] != draft["diff"]["new_checksum"]

        draft_file = workspace_path / ".weagent" / "drafts" / "skills" / "skill-1" / "agent-1.json"
        assert json.loads(draft_file.read_text(encoding="utf-8"))["full_markdown"] == draft["full_markdown"]
        assert collect_skill_draft_payloads(
            "agent-1",
            "session-1",
            workspace_root=str(workspace_path),
        ) == []


def test_skill_draft_sync_persists_pending_review_without_upgrading_binding(app_context):
    _user, agent = _create_user_and_agent()
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Runtime Skill",
        markdown="# Runtime Skill\nOriginal.",
    )
    assert error is None
    original_version_id = skill["latest_version"]["id"]
    bind_result, bind_error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=original_version_id,
        granted_permissions=[],
    )
    assert bind_error is None

    result, error = capability_draft_sync_service.sync_records(
        user_id="user-1",
        records=[
            {
                "session_id": "session-1",
                "agent_id": agent.id,
                "source_skill_id": skill["id"],
                "source_version_id": original_version_id,
                "runtime_id": skill["id"],
                "diff": {"changed": ["SKILL.md"], "new_checksum": "sha256:new"},
                "full_markdown": "# Runtime Skill\nUpdated by agent.",
            }
        ],
    )

    assert error is None
    assert len(result) == 1
    draft = SkillRevisionDraft.query.one()
    assert draft.status == "pending_review"
    assert draft.full_markdown.endswith("Updated by agent.")

    duplicate, duplicate_error = capability_draft_sync_service.sync_records(
        user_id="user-1",
        records=[
            {
                "session_id": "session-1",
                "agent_id": agent.id,
                "source_skill_id": skill["id"],
                "source_version_id": original_version_id,
                "diff": {"changed": ["SKILL.md"], "new_checksum": "sha256:new"},
                "full_markdown": "# Runtime Skill\nUpdated by agent.",
            }
        ],
    )
    assert duplicate_error is None
    assert duplicate[0]["id"] == draft.id
    assert SkillRevisionDraft.query.count() == 1

    published, publish_error = capability_service.publish_draft(
        user_id="user-1",
        draft_id=draft.id,
        version="1.0.1",
    )
    assert publish_error is None
    assert published["version"]["id"] != original_version_id
    assert AgentCapabilityBinding.query.get(bind_result["id"]).capability_version_id == original_version_id


def test_draft_sync_api_and_manager_persist_runtime_skill_drafts(client_context):
    client, headers, user, agent = client_context
    skill, error = capability_service.create_skill(
        user_id=user.id,
        name="Runtime Skill",
        markdown="# Runtime Skill\nOriginal.",
    )
    assert error is None

    response = client.post(
        "/api/capabilities/drafts/sync",
        headers=headers,
        json={
            "records": [
                {
                    "session_id": "session-api",
                    "agent_id": agent.id,
                    "source_skill_id": skill["id"],
                    "source_version_id": skill["latest_version"]["id"],
                    "diff": {"changed": ["SKILL.md"], "new_checksum": "sha256:api"},
                    "full_markdown": "# Runtime Skill\nAPI sync.",
                }
            ]
        },
    )

    assert response.status_code == 201
    assert response.get_json()["data"][0]["status"] == "pending_review"

    conversation = Conversation(
        id="session-manager",
        title="Draft Sync Session",
        type="single",
        owner_id=user.id,
        sandbox_session_id="session-manager",
        sandbox_status="running",
    )
    db.session.add(conversation)
    db.session.commit()

    class FakeClient:
        def send_to_agent(self, _agent_id, _message):
            return {
                "status": "ok",
                "reply": "done",
                "skill_drafts": [
                    {
                        "session_id": "session-manager",
                        "agent_id": agent.id,
                        "source_skill_id": skill["id"],
                        "source_version_id": skill["latest_version"]["id"],
                        "diff": {
                            "changed": ["SKILL.md"],
                            "new_checksum": "sha256:manager",
                        },
                        "full_markdown": "# Runtime Skill\nManager sync.",
                    }
                ],
            }

    class FakeSession:
        session_id = "session-manager"
        client = FakeClient()

    manager = DockerContainerManager()
    manager._sessions["session-manager"] = FakeSession()
    manager.recover_sessions = lambda: None

    result = manager.send_message("session-manager", agent.id, "run")

    assert result["status"] == "ok"
    assert result["skill_drafts_sync"]["status"] == "ok"
    assert SkillRevisionDraft.query.count() == 2
