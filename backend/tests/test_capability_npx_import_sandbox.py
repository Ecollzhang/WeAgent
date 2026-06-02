import subprocess

import pytest

from app import create_app, db
from app.models.user import User
from app.services.capability_npx_import_sandbox import (
    capability_npx_import_sandbox,
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


def create_user(user_id="npx-user"):
    user = User(
        id=user_id,
        username=f"{user_id}-name",
        email=f"{user_id}@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_npx_preview_runs_in_docker_with_isolated_agent_homes(app_context):
    create_user()
    captured = {}

    def fake_runner(command, import_root, timeout):
        captured["command"] = command
        captured["timeout"] = timeout
        skill_dir = import_root / ".codex" / "skills" / "web-access"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Web Access\n", encoding="utf-8")
        return {"returncode": 0, "stdout": "installed", "stderr": ""}

    preview, error = capability_npx_import_sandbox.preview_npx(
        user_id="npx-user",
        source_ref="npx skills add eze-is/web-access",
        runner=fake_runner,
    )

    assert error is None
    command = captured["command"]
    assert command[:3] == ["docker", "run", "--rm"]
    assert "HOME=/import-home" in command
    assert "CODEX_HOME=/import-home/.codex" in command
    assert "CLAUDE_HOME=/import-home/.claude" in command
    assert "AGENTS_HOME=/import-home/.agents" in command
    assert "NPM_CONFIG_YES=true" in command
    assert "NPM_CONFIG_UPDATE_NOTIFIER=false" in command
    assert "NPM_CONFIG_LOGLEVEL=error" in command
    assert "node:22" in command
    assert "node:22-alpine" not in command
    assert command[-7:] == [
        "npx",
        "--yes",
        "skills",
        "add",
        "--yes",
        "--global",
        "eze-is/web-access",
    ]
    assert preview["source_type"] == "npx"
    assert preview["capabilities"][0]["name"] == "Web Access"


def test_npx_preview_rejects_shell_injection_before_docker(app_context):
    create_user()

    preview, error = capability_npx_import_sandbox.preview_npx(
        user_id="npx-user",
        source_ref="npx skills add eze-is/web-access && whoami",
        runner=lambda command, import_root, timeout: (_ for _ in ()).throw(AssertionError("runner should not be called")),
    )

    assert preview is None
    assert "not allowed" in error or "Unsupported" in error


def test_npx_preview_reports_docker_unavailable(app_context):
    create_user()

    def missing_docker(_command, _import_root, _timeout):
        raise FileNotFoundError("docker")

    preview, error = capability_npx_import_sandbox.preview_npx(
        user_id="npx-user",
        source_ref="npx @orchestra-research/ai-research-skills",
        runner=missing_docker,
    )

    assert preview is None
    assert "Docker import sandbox unavailable" in error


def test_npx_preview_reports_timeout_without_cleanup_error(app_context):
    create_user()

    def timeout_runner(command, import_root, timeout):
        skill_dir = import_root / ".npm" / "_npx" / "partial"
        skill_dir.mkdir(parents=True)
        (skill_dir / "output.log").write_text("partial", encoding="utf-8")
        raise subprocess.TimeoutExpired(command, timeout)

    preview, error = capability_npx_import_sandbox.preview_npx(
        user_id="npx-user",
        source_ref="npx @orchestra-research/ai-research-skills",
        runner=timeout_runner,
        timeout=3,
    )

    assert preview is None
    assert "timed out after 3 seconds" in error
