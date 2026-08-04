import importlib
import json
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.conversation import Conversation
from app.models.user import User
from app.models.workspace import Workspace
from app.sandbox.container import tools as container_tools


conversation_module = importlib.import_module(
    "app.services.conversation_service"
)
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class _Response:
    status = 200
    headers = {"content-type": "application/json"}

    def __init__(self):
        self.request = None

    def read(self):
        return json.dumps({"data": {"results": [], "total": 0}}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def test_background_sandbox_restore_has_no_request_authorization_header():
    app = create_app("testing")

    with app.app_context():
        assert conversation_module._current_authorization_header() == ""


def test_generic_rag_service_call_cannot_widen_server_issued_scope():
    response = _Response()

    def fake_open(request, timeout):
        response.request = request
        return response

    env = {
        "SERVICE_REGISTRY": json.dumps(
            {"rag": "http://host.docker.internal:5104"}
        ),
        "USER_AUTH_TOKEN": "Bearer user-controlled-token",
        "RAG_INTERNAL_API_KEY": "test-only",
        "RAG_SCOPE_USER_ID": "teacher-1",
        "RAG_SCOPE_DOMAIN": "edu",
        "RAG_SCOPE_WORKSPACE_ID": "workspace-allowed",
    }
    with (
        patch.dict("os.environ", env, clear=False),
        patch("urllib.request.urlopen", side_effect=fake_open),
    ):
        container_tools._call_service_api(
            "rag",
            "POST",
            "/api/rag/search",
            body={
                "query": "lesson",
                "domain": "rd",
                "workspace_id": "workspace-other",
            },
        )

    payload = json.loads(response.request.data)
    assert payload["domain"] == "edu"
    assert payload["workspace_id"] == "workspace-allowed"
    assert response.request.headers["X-weagent-user-id"] == "teacher-1"
    assert response.request.headers["X-weagent-domain"] == "edu"
    assert "Authorization" not in response.request.headers


def test_rd_shortcut_conversation_preserves_project_and_service_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(
            User(
                id="domain-owner",
                username="domain-owner",
                email="domain-owner@example.com",
                password_hash="hash",
            )
        )
        db.session.add(
            Workspace(
                id="domain-rd-workspace",
                user_id="domain-owner",
                domain="rd",
                name="研发空间",
            )
        )
        db.session.commit()

    response = app.test_client().post(
        "/api/conversations",
        headers=_headers(app, "domain-owner"),
        json={
            "title": "继续分析当前研发项目",
            "type": "single",
            "participant_ids": [],
            "kb_domain": "rd",
            "workspace_context": {"domain": "rd"},
            "services": ["rd", "rag"],
            "project_id": "project-42",
            "kb_document_ids": ["doc-1"],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["workspace_id"] == "domain-rd-workspace"
    assert payload["services"] == ["rd", "rag"]
    assert payload["project_id"] == "project-42"
    assert payload["kb_document_ids"] == ["doc-1"]

    with app.app_context():
        stored = db.session.get(Conversation, payload["id"])
        assert stored.services == ["rd", "rag"]
        assert stored.project_id == "project-42"
        db.session.remove()
        db.drop_all()


def test_core_conversation_persists_server_agent_service_views():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(
            User(
                id="edu-owner",
                username="edu-owner",
                email="edu-owner@example.com",
                password_hash="hash",
            )
        )
        db.session.commit()

    response = app.test_client().post(
        "/api/conversations",
        headers=_headers(app, "edu-owner"),
        json={
            "title": "Education service views",
            "type": "single",
            "participant_ids": [],
            "kb_domain": "edu",
            "workspace_context": {"domain": "edu", "role": "teacher"},
            "services": ["edu", "rag"],
            "agent_configs": {
                "_edu_8": {
                    "adapter_name": "codex",
                    "allowed_services": ["edu", "rag"],
                },
                "_edu_9": {
                    "adapter_name": "codex",
                    "allowed_services": ["edu"],
                },
            },
        },
    )

    assert response.status_code == 201
    conversation_id = response.get_json()["data"]["id"]
    with app.app_context():
        stored = db.session.get(Conversation, conversation_id)
        assert stored.sandbox_agent_service_views == {
            "_edu_8": ["edu", "rag"],
            "_edu_9": ["edu"],
        }
        db.session.remove()
        db.drop_all()


def test_domain_migration_uses_existing_conversation_columns_safely():
    migration = (
        BACKEND_ROOT / "sql" / "migration_v2.sql"
    ).read_text(encoding="utf-8")

    assert (
        "ADD COLUMN IF NOT EXISTS `workspace_id` VARCHAR(36) DEFAULT NULL;"
        in migration
    )
    assert (
        "ADD COLUMN IF NOT EXISTS `kb_domain` VARCHAR(20) "
        "NOT NULL DEFAULT '';"
        in migration
    )
    assert (
        "ADD COLUMN IF NOT EXISTS `kb_document_ids` JSON DEFAULT NULL;"
        in migration
    )
    assert "`domains` JSON DEFAULT NULL" in migration
    assert "AFTER `user_id`" not in migration
    assert "AFTER `kb_document_ids`" not in migration


def test_standalone_domain_services_inherit_backend_environment():
    for service in ("rd", "rag"):
        source = (
            BACKEND_ROOT / "services" / service / "config.py"
        ).read_text(encoding="utf-8")

        assert "_BACKEND_DIR" in source
        assert "os.path.join(_BACKEND_DIR, '.env')" in source


def test_sandbox_host_forwards_selected_services_and_project_context():
    source = (
        BACKEND_ROOT / "app" / "sandbox" / "host" / "manager.py"
    ).read_text(encoding="utf-8")

    assert '"CONVERSATION_SERVICES"' in source
    assert '"RD_PROJECT_ID"' in source
