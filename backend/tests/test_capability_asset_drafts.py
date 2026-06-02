import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import (
    CapabilitySecurityAudit,
    CapabilityVersionAsset,
    SkillRevisionDraft,
)
from app.models.user import User
from app.sandbox.container.capabilities import (
    collect_skill_draft_payloads,
    write_projection,
)
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
                "assets": [
                    {
                        "path": "scripts/check.mjs",
                        "kind": "script",
                        "content": "console.log('original')\n",
                    }
                ],
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
                    "grants": [],
                },
            }
        },
    }


def test_runtime_asset_change_collects_file_level_draft_payload():
    with _workspace_tempdir() as workspace:
        workspace_path = Path(workspace)
        write_projection(_skill_projection(), workspace_root=str(workspace_path))

        script_path = workspace_path / ".weagent" / "skills" / "skill-1" / "scripts" / "check.mjs"
        assert script_path.read_text(encoding="utf-8") == "console.log('original')\n"
        script_path.write_text("console.log('updated')\n", encoding="utf-8")

        drafts = collect_skill_draft_payloads(
            "agent-1",
            "session-1",
            workspace_root=str(workspace_path),
        )

        assert len(drafts) == 1
        draft = drafts[0]
        assert draft["full_markdown"] == "# Runtime Skill\nOriginal instructions."
        assert draft["diff"]["changed"] == ["scripts/check.mjs"]
        assert draft["diff"]["files"][0]["path"] == "scripts/check.mjs"
        assert draft["diff"]["proposed_assets"] == [
            {
                "path": "scripts/check.mjs",
                "kind": "script",
                "content": "console.log('updated')\n",
                "mime_type": "text/plain",
            }
        ]
        assert draft["diff"]["old_checksum"] != draft["diff"]["new_checksum"]

        draft_file = workspace_path / ".weagent" / "drafts" / "skills" / "skill-1" / "agent-1.json"
        saved = json.loads(draft_file.read_text(encoding="utf-8"))
        assert saved["diff"]["changed"] == ["scripts/check.mjs"]
        assert collect_skill_draft_payloads(
            "agent-1",
            "session-1",
            workspace_root=str(workspace_path),
        ) == []


def test_asset_draft_publish_creates_new_version_with_assets_and_audit(app_context):
    _user, agent = _create_user_and_agent()
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Runtime Skill",
        markdown="# Runtime Skill\nOriginal.",
        assets=[
            {
                "path": "scripts/check.mjs",
                "kind": "script",
                "content": "console.log('original')\n",
            }
        ],
    )
    assert error is None
    original_version_id = skill["latest_version"]["id"]

    result, error = capability_draft_sync_service.sync_records(
        user_id="user-1",
        records=[
            {
                "session_id": "session-1",
                "agent_id": agent.id,
                "source_skill_id": skill["id"],
                "source_version_id": original_version_id,
                "runtime_id": skill["id"],
                "diff": {
                    "changed": ["scripts/check.mjs"],
                    "new_checksum": "sha256:updated",
                    "proposed_assets": [
                        {
                            "path": "scripts/check.mjs",
                            "kind": "script",
                            "content": "console.log('updated')\n",
                        }
                    ],
                },
                "full_markdown": "# Runtime Skill\nOriginal.",
            }
        ],
    )
    assert error is None

    draft = SkillRevisionDraft.query.get(result[0]["id"])
    published, publish_error = capability_service.publish_draft(
        user_id="user-1",
        draft_id=draft.id,
        version="1.0.1",
    )

    assert publish_error is None
    new_version_id = published["version"]["id"]
    assert new_version_id != original_version_id
    new_asset = CapabilityVersionAsset.query.filter_by(
        capability_version_id=new_version_id,
        path="scripts/check.mjs",
    ).one()
    assert new_asset.content == "console.log('updated')\n"
    original_asset = CapabilityVersionAsset.query.filter_by(
        capability_version_id=original_version_id,
        path="scripts/check.mjs",
    ).one()
    assert original_asset.content == "console.log('original')\n"
    audit = CapabilitySecurityAudit.query.filter_by(draft_id=draft.id).one()
    assert audit.capability_version_id == new_version_id
    assert audit.risk_level in {"low", "medium"}


def test_high_risk_asset_draft_publish_requires_expert_override(app_context):
    _user, agent = _create_user_and_agent()
    skill, error = capability_service.create_skill(
        user_id="user-1",
        name="Runtime Skill",
        markdown="# Runtime Skill\nOriginal.",
        assets=[],
    )
    assert error is None
    original_version_id = skill["latest_version"]["id"]
    result, error = capability_draft_sync_service.sync_records(
        user_id="user-1",
        records=[
            {
                "session_id": "session-1",
                "agent_id": agent.id,
                "source_skill_id": skill["id"],
                "source_version_id": original_version_id,
                "runtime_id": skill["id"],
                "diff": {
                    "changed": ["scripts/leak.mjs"],
                    "new_checksum": "sha256:high-risk",
                    "proposed_assets": [
                        {
                            "path": "scripts/leak.mjs",
                            "kind": "script",
                            "content": "console.log(process.env.SECRET)\n",
                        }
                    ],
                },
                "full_markdown": "# Runtime Skill\nOriginal.",
            }
        ],
    )
    assert error is None
    draft = SkillRevisionDraft.query.get(result[0]["id"])

    blocked, blocked_error = capability_service.publish_draft(
        user_id="user-1",
        draft_id=draft.id,
        version="1.0.1",
    )

    assert blocked is None
    assert blocked_error == "High-risk audit requires expert override"
    assert CapabilitySecurityAudit.query.filter_by(draft_id=draft.id).count() == 0

    published, publish_error = capability_service.publish_draft(
        user_id="user-1",
        draft_id=draft.id,
        version="1.0.1",
        override_confirmed=True,
        override_reason="Reviewed and accepted for test fixture.",
    )

    assert publish_error is None
    audit = CapabilitySecurityAudit.query.filter_by(draft_id=draft.id).one()
    assert audit.capability_version_id == published["version"]["id"]
    assert audit.risk_level == "high"
    assert audit.overridden is True
