import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.sandbox.container import tools as container_tools


RAG_SERVICE = Path(__file__).resolve().parents[1] / "services" / "rag"
SPEC = importlib.util.spec_from_file_location(
    "education_rag_access_scope",
    RAG_SERVICE / "access_scope.py",
)
access_scope = importlib.util.module_from_spec(SPEC)
sys_modules = __import__("sys").modules
sys_modules[SPEC.name] = access_scope
SPEC.loader.exec_module(access_scope)
resolve_search_scope = access_scope.resolve_search_scope


def test_internal_search_scope_rejects_model_requested_workspace_override():
    with pytest.raises(PermissionError, match="workspace"):
        resolve_search_scope(
            internal=True,
            headers={
                "X-WeAgent-User-ID": "teacher-1",
                "X-WeAgent-Domain": "edu",
                "X-WeAgent-Workspace-ID": "workspace-allowed",
            },
            payload={
                "domain": "edu",
                "workspace_id": "workspace-other",
            },
        )


def test_jwt_search_scope_is_bound_to_authenticated_user():
    scope = resolve_search_scope(
        internal=False,
        headers={},
        payload={"domain": "edu", "workspace_id": "workspace-1"},
        jwt_identity="student-1",
    )

    assert scope.user_id == "student-1"
    assert scope.domain == "edu"
    assert scope.workspace_id == "workspace-1"
    assert scope.internal is False


class _Response:
    status = 200
    headers = {"content-type": "application/json"}

    def __init__(self):
        self.request = None

    def read(self):
        return json.dumps(
            {"data": {"query": "lesson", "results": [], "total": 0}}
        ).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_sandbox_rag_search_uses_server_scope_not_tool_arguments():
    response = _Response()

    def fake_open(request, timeout):
        response.request = request
        return response

    env = {
        "RAG_SCOPE_USER_ID": "teacher-1",
        "RAG_SCOPE_DOMAIN": "edu",
        "RAG_SCOPE_WORKSPACE_ID": "workspace-allowed",
        "RAG_INTERNAL_API_KEY": "test-only",
    }
    with (
        patch.dict("os.environ", env, clear=False),
        patch("urllib.request.urlopen", side_effect=fake_open),
    ):
        container_tools._rag_search(
            "lesson",
            domain="rd",
            workspace_id="workspace-other",
        )

    payload = json.loads(response.request.data)
    assert payload["domain"] == "edu"
    assert payload["workspace_id"] == "workspace-allowed"
    assert response.request.headers["X-weagent-user-id"] == "teacher-1"


def test_sandbox_rag_search_requires_server_issued_scope():
    with patch.dict(
        "os.environ",
        {
            "RAG_SCOPE_USER_ID": "",
            "RAG_SCOPE_DOMAIN": "",
            "RAG_SCOPE_WORKSPACE_ID": "",
        },
        clear=False,
    ):
        with pytest.raises(RuntimeError, match="scope"):
            container_tools._rag_search("lesson")
