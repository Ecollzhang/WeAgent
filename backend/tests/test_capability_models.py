import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import (
    AgentCapabilityBinding,
    Capability,
    CapabilityCallRecord,
    CapabilityVersion,
    SkillRevisionDraft,
)


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_capability_version_stores_peer_type_and_meta(app_context):
    capability = Capability(
        type="skill",
        name="Code Review",
        slug="code-review",
        description="Review code changes",
        source="user",
        source_ref="manual",
    )
    version = CapabilityVersion(
        capability=capability,
        version="1.0.0",
        content="# Code Review\nCheck bugs first.",
        manifest={"entry": "SKILL.md"},
        permissions={"required": ["read_workspace"], "optional": []},
        meta={"format": "markdown"},
        checksum="sha256:test",
    )

    db.session.add(version)
    db.session.commit()

    saved = Capability.query.filter_by(slug="code-review").one()
    assert saved.type == "skill"
    assert saved.versions[0].meta == {"format": "markdown"}
    assert "metadata" not in saved.versions[0].__table__.columns


def test_agent_binding_pins_version_and_authorization_snapshot(app_context):
    agent = Agent(name="Reviewer", agent_type="custom", adapter_name="claude")
    capability = Capability(type="tool", name="Read File", slug="read-file", source="builtin")
    version = CapabilityVersion(
        capability=capability,
        version="1.0.0",
        permissions={"required": ["read_workspace"], "optional": []},
        meta={"builtin": True},
    )
    binding = AgentCapabilityBinding(
        agent=agent,
        capability=capability,
        capability_version=version,
        enabled=True,
        version_policy="pinned",
        granted_permissions=["read_workspace"],
        authorization_snapshot={
            "capability_id": "pending",
            "version": "1.0.0",
            "granted_permissions": ["read_workspace"],
        },
    )

    db.session.add(binding)
    db.session.commit()

    saved = AgentCapabilityBinding.query.one()
    assert saved.agent.name == "Reviewer"
    assert saved.capability.type == "tool"
    assert saved.capability_version.version == "1.0.0"
    assert saved.version_policy == "pinned"
    assert saved.granted_permissions == ["read_workspace"]


def test_call_record_and_skill_draft_round_trip(app_context):
    capability = Capability(type="skill", name="Planner", slug="planner", source="user")
    version = CapabilityVersion(
        capability=capability,
        version="1.0.0",
        content="# Planner",
        permissions={"required": ["modify_skill"], "optional": []},
    )
    call = CapabilityCallRecord(
        session_id="session-1",
        run_id="run-1",
        agent_id="agent-1",
        capability=capability,
        capability_version=version,
        call_type="tool",
        tool_name="report_progress",
        permissions_used=["modify_skill"],
        input_summary={"text": "start"},
        output_summary={"status": "ok"},
        status="completed",
    )
    draft = SkillRevisionDraft(
        source_skill=capability,
        source_version=version,
        session_id="session-1",
        agent_id="agent-1",
        diff={"changed": ["SKILL.md"]},
        full_markdown="# Planner\nUpdated by agent.",
        status="pending_review",
    )

    db.session.add_all([call, draft])
    db.session.commit()

    assert CapabilityCallRecord.query.one().status == "completed"
    assert SkillRevisionDraft.query.one().status == "pending_review"
