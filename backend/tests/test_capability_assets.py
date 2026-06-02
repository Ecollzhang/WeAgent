import pytest

from app import create_app, db
from app.models.capability import (
    Capability,
    CapabilityImportJob,
    CapabilitySecurityAudit,
    CapabilityVersion,
    CapabilityVersionAsset,
)
from app.models.user import User
from app.services.capability_service import capability_service


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_asset_import_job_and_security_audit_models_persist(app_context):
    user = User(
        id="user-assets",
        username="asset-user",
        email="asset-user@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.flush()

    capability = Capability(
        user_id=user.id,
        type="skill",
        name="Bundle Skill",
        slug="bundle-skill",
        source="upload",
        source_ref="bundle.zip",
    )
    db.session.add(capability)
    db.session.flush()
    version = CapabilityVersion(
        capability=capability,
        version="1.0.0",
        content="# Bundle Skill",
        manifest={"entry": "SKILL.md"},
        permissions={"required": [], "optional": []},
    )
    db.session.add(version)
    db.session.flush()
    asset = CapabilityVersionAsset(
        capability_version_id=version.id,
        path="scripts/check.mjs",
        kind="script",
        content="console.log('ok')",
        size=17,
        sha256="sha256:test",
        mime_type="text/javascript",
    )
    job = CapabilityImportJob(
        user_id=user.id,
        source_type="upload",
        source_ref="bundle.zip",
        status="previewed",
        preview_payload={"capabilities": []},
        audit_summary={"risk_level": "low"},
    )
    audit = CapabilitySecurityAudit(
        user_id=user.id,
        capability=capability,
        capability_version=version,
        risk_level="low",
        risk_items=[],
        blocking_items=[],
        inferred_permissions=[],
    )
    db.session.add_all([asset, job, audit])
    db.session.commit()

    assert CapabilityVersionAsset.query.filter_by(path="scripts/check.mjs").count() == 1
    assert CapabilityImportJob.query.filter_by(source_ref="bundle.zip").one().status == "previewed"
    assert CapabilitySecurityAudit.query.one().risk_level == "low"


def test_version_checksum_changes_when_assets_change(app_context):
    user = User(
        id="user-checksum",
        username="checksum-user",
        email="checksum-user@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.commit()

    first, error = capability_service.create_skill(
        user_id=user.id,
        name="Asset Skill",
        markdown="# Asset Skill",
        assets=[{"path": "scripts/check.mjs", "content": "console.log('v1')", "kind": "script"}],
    )
    assert error is None
    first_checksum = first["latest_version"]["checksum"]

    second, error = capability_service.create_version(
        capability_id=first["id"],
        content="# Asset Skill",
        permissions={"required": [], "optional": []},
        assets=[{"path": "scripts/check.mjs", "content": "console.log('v2')", "kind": "script"}],
    )

    assert error is None
    assert second["checksum"] != first_checksum
