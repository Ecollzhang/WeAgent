import base64
import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import Capability
from app.models.user import User
from app.sandbox.container.capabilities import write_projection, write_run_snapshot
from app.sandbox.container.tools import ToolRegistry, register_builtin_tools
from app.services.capability_projection_service import build_capability_projection
from app.services.capability_service import capability_service
from app.services.tool_provider_config_service import tool_provider_config_service


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
    "WjR9awAAAABJRU5ErkJggg=="
)


class SearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = self.path.split("q=", 1)[-1].split("&", 1)[0]
        body = json.dumps({
            "results": [
                {
                    "title": "Fixture Result",
                    "url": "https://example.test/result",
                    "snippet": f"query={query}",
                }
            ]
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _workspace_tempdir():
    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=base)


def _create_user_and_agent():
    user = User(
        id="user-1",
        username="runtime-user",
        email="runtime@example.com",
        password_hash="hash",
    )
    agent = Agent(
        id="agent-runtime",
        name="Runtime Agent",
        agent_type="custom",
        adapter_name="claude",
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add_all([user, agent])
    db.session.commit()
    return user, agent


def _enable_config(user_id, source_ref, provider_type, config):
    capability = Capability.query.filter_by(source_ref=source_ref).one()
    created, error = tool_provider_config_service.create_config(
        user_id=user_id,
        capability_id=capability.id,
        profile_name=f"{source_ref} profile",
        provider_type=provider_type,
        config=config,
        secret_refs=["TEST_SECRET_ALIAS"] if provider_type in {"database", "http"} else [],
    )
    assert error is None
    tested, error = tool_provider_config_service.test_config(
        user_id=user_id,
        capability_id=capability.id,
        config_id=created["id"],
    )
    assert error is None
    assert tested["last_test_status"] == "passed"
    enabled, error = tool_provider_config_service.enable_config(
        user_id=user_id,
        capability_id=capability.id,
        config_id=created["id"],
    )
    assert error is None
    assert enabled["status"] == "valid"
    return capability


def _bind(agent, capability, permissions):
    result, error = capability_service.bind_to_user_agent(
        user_id=agent.user_id,
        agent_id=agent.id,
        capability_version_id=capability.latest_version_id,
        granted_permissions=permissions,
    )
    assert error is None
    return result


def test_configured_tools_project_run_and_record_calls(app_context):
    user, agent = _create_user_and_agent()
    capability_service.seed_builtin_tool_capabilities()

    server = ThreadingHTTPServer(("127.0.0.1", 0), SearchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with _workspace_tempdir() as workspace:
        root = Path(workspace)
        (root / "image.png").write_bytes(base64.b64decode(PNG_1X1))
        sqlite_path = root / "data.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("CREATE TABLE users (name TEXT, score INTEGER)")
        conn.execute("INSERT INTO users VALUES ('alice', 10)")
        conn.commit()
        conn.close()

        web_search = _enable_config(
            user.id,
            "web_search",
            "http",
            {"endpoint": f"http://127.0.0.1:{server.server_port}/search"},
        )
        image_analysis = _enable_config(
            user.id,
            "image_analysis",
            "model",
            {"model": "vision-fixture"},
        )
        image_generation = _enable_config(
            user.id,
            "image_generation",
            "model",
            {"model": "image-fixture", "output_format": "png"},
        )
        database_query = _enable_config(
            user.id,
            "database_query",
            "database",
            {
                "driver": "sqlite",
                "connection_alias": "WORKSPACE_DB",
                "readonly": True,
                "path": "data.db",
            },
        )

        _bind(agent, web_search, ["network"])
        _bind(agent, image_analysis, ["read_workspace"])
        _bind(agent, image_generation, ["write_workspace", "network", "use_secret"])
        _bind(agent, database_query, ["read_workspace", "use_secret"])

        projection = build_capability_projection(
            session_id="session-runtime",
            agents=[{"agent_id": agent.id, "role": agent.name}],
            workspace_root=str(root),
        )
        assert projection["tools"][web_search.id]["status"] == "implemented"
        assert projection["tools"][web_search.id]["provider_config"]["provider_type"] == "http"
        assert "TEST_SECRET_ALIAS" not in json.dumps(projection)

        write_projection(projection, workspace_root=str(root))
        write_run_snapshot(projection, "run-runtime", workspace_root=str(root))
        registry = ToolRegistry(workspace_root=str(root))
        register_builtin_tools(registry)

        search = json.loads(registry.call_from_agent(
            agent.id,
            "web_search",
            {"query": "weagent", "max_results": 1},
            run_id="run-runtime",
            session_id="session-runtime",
        ))
        assert search["status"] == "ok"
        assert search["result"]["results"][0]["title"] == "Fixture Result"

        analysis = json.loads(registry.call_from_agent(
            agent.id,
            "image_analysis",
            {"path": "image.png", "prompt": "describe"},
            run_id="run-runtime",
            session_id="session-runtime",
        ))
        assert analysis["status"] == "ok"
        assert analysis["result"]["image"]["format"] == "PNG"

        generated = json.loads(registry.call_from_agent(
            agent.id,
            "image_generate",
            {"prompt": "fixture", "output_path": "generated/out.png"},
            run_id="run-runtime",
            session_id="session-runtime",
        ))
        assert generated["status"] == "ok"
        assert (root / "generated" / "out.png").exists()

        rows = json.loads(registry.call_from_agent(
            agent.id,
            "database_query",
            {"query": "SELECT name, score FROM users", "max_rows": 5},
            run_id="run-runtime",
            session_id="session-runtime",
        ))
        assert rows["status"] == "ok"
        assert rows["result"]["rows"] == [["alice", 10]]

        calls = (root / ".weagent" / "runs" / "run-runtime" / "calls.jsonl").read_text(
            encoding="utf-8"
        ).strip().splitlines()
        assert len(calls) == 4
        assert {json.loads(line)["tool_name"] for line in calls} == {
            "web_search",
            "image_analysis",
            "image_generate",
            "database_query",
        }

    server.shutdown()
    server.server_close()
