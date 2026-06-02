import base64
import json
import os
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, "/app")

from container.capabilities import write_projection, write_run_snapshot  # noqa: E402
from container.tools import ToolRegistry, register_builtin_tools  # noqa: E402


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
AGENT_ID = "uat-agent"
LIMITED_AGENT_ID = "limited-agent"
SESSION_ID = "toolset-005-docker-uat"
RUN_ID = "toolset-005-run"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


TOOL_DEFS = [
    ("code_search", "Code Search", "code.search", ["code_search"], ["read_workspace"]),
    ("code_review", "Code Review Scan", "code.review_scan", ["code_review_scan"], ["read_workspace"]),
    (
        "file_operations",
        "File Operations",
        "workspace.files",
        ["read_file", "write_file", "list_files"],
        ["read_workspace", "write_workspace"],
    ),
    (
        "document_parse",
        "Document Text Extract",
        "document.text_extract",
        ["document_text_extract"],
        ["read_workspace"],
    ),
    ("web_fetch", "HTTP Fetch", "network.http_fetch", ["http_fetch"], ["network"]),
    ("api_client", "API Client", "network.api_request", ["api_request"], ["network"]),
    (
        "data_analysis",
        "Data Analysis",
        "data.readonly",
        ["csv_profile", "json_query", "sqlite_query_readonly"],
        ["read_workspace"],
    ),
    ("image_info", "Image Info", "image.info", ["image_info"], ["read_workspace"]),
    ("terminal", "Safe Terminal", "terminal.safe", ["run_command_safe"], ["run_command"]),
    (
        "git_operations",
        "Git Operations",
        "git.readonly",
        ["git_status", "git_diff", "git_log"],
        ["read_workspace"],
    ),
]


def ensure_fixtures() -> None:
    (WORKSPACE / "src").mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "docs").mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "data").mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "assets").mkdir(parents=True, exist_ok=True)

    (WORKSPACE / "src" / "sample.py").write_text(
        "import os\n\n# TODO: review this sample\nsecret = 'demo'\nos.system('echo risky')\n",
        encoding="utf-8",
    )
    (WORKSPACE / "docs" / "note.md").write_text(
        "# UAT Note\n\nThis document proves document_text_extract works.\n",
        encoding="utf-8",
    )
    (WORKSPACE / "data" / "sample.csv").write_text(
        "name,score\nalice,9\nbob,8\n",
        encoding="utf-8",
    )
    (WORKSPACE / "data" / "sample.json").write_text(
        json.dumps({"items": [{"name": "alpha"}, {"name": "beta"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (WORKSPACE / "assets" / "pixel.png").write_bytes(PNG_1X1)

    db_path = WORKSPACE / "data" / "sample.sqlite"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO items(name) VALUES (?)", [("alpha",), ("beta",)])
    conn.commit()
    conn.close()

    subprocess.run(["git", "init"], cwd=WORKSPACE, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "uat@example.test"],
        cwd=WORKSPACE,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "WeAgent UAT"],
        cwd=WORKSPACE,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "src/sample.py", "docs/note.md", "data/sample.csv", "data/sample.json", "assets/pixel.png"],
        cwd=WORKSPACE,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "seed docker smoke fixtures"],
        cwd=WORKSPACE,
        check=True,
        capture_output=True,
        text=True,
    )


def tool_manifest(handler: str, tool_names: list[str], status: str = "implemented") -> dict:
    return {
        "schema_version": "weagent.tool/v1",
        "runtime": "builtin",
        "handler": handler,
        "tool_names": tool_names,
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "ui": {"status": status},
    }


def build_projection() -> dict:
    projection = {
        "schema_version": "weagent.capability_projection/v1",
        "session_id": SESSION_ID,
        "workspace_root": "/workspace",
        "capabilities": {},
        "skills": {},
        "mcp": {},
        "plugins": {},
        "tools": {},
        "agents": {
            AGENT_ID: {
                "agent_id": AGENT_ID,
                "capabilities": [],
                "skill_index": [],
                "tool_index": [],
                "permissions": {"agent_id": AGENT_ID, "grants": []},
            },
            LIMITED_AGENT_ID: {
                "agent_id": LIMITED_AGENT_ID,
                "capabilities": [],
                "skill_index": [],
                "tool_index": [],
                "permissions": {"agent_id": LIMITED_AGENT_ID, "grants": []},
            },
        },
    }

    def add_tool(source_ref, name, handler, tool_names, permissions, agent_id=AGENT_ID, status="implemented"):
        capability_id = f"tool-{source_ref}"
        version_id = f"{capability_id}-v1"
        manifest = tool_manifest(handler, tool_names, status)
        projection["capabilities"][capability_id] = {
            "id": capability_id,
            "capability_id": capability_id,
            "type": "tool",
            "name": name,
            "source": "builtin",
            "source_ref": source_ref,
            "version": {"id": version_id, "version": "1.0.0", "manifest": manifest},
        }
        projection["tools"][capability_id] = {
            "runtime_id": capability_id,
            "capability_id": capability_id,
            "version_id": version_id,
            "name": name,
            "description": f"UAT fixture for {name}.",
            "content": f"# {name}\n\nDocker UAT fixture documentation for {name}.\n",
            "source": "builtin",
            "source_ref": source_ref,
            "manifest": manifest,
            "permissions": {"required": permissions, "optional": []},
            "tool_names": tool_names,
            "handler": handler,
            "status": status,
            "doc_path": f"/workspace/.weagent/tools/{capability_id}/TOOL.md",
            "manifest_path": f"/workspace/.weagent/tools/{capability_id}/manifest.json",
        }
        view = {
            "binding_id": f"binding-{agent_id}-{source_ref}",
            "runtime_id": capability_id,
            "capability_id": capability_id,
            "capability_version_id": version_id,
            "type": "tool",
            "name": name,
            "source": "builtin",
            "source_ref": source_ref,
            "version": "1.0.0",
            "granted_permissions": permissions,
            "manifest": manifest,
            "tool_names": tool_names,
            "status": status,
        }
        projection["agents"][agent_id]["capabilities"].append(view)
        projection["agents"][agent_id]["tool_index"].append(
            {
                "runtime_id": capability_id,
                "capability_id": capability_id,
                "version_id": version_id,
                "name": name,
                "description": f"UAT fixture for {name}.",
                "tool_names": tool_names,
                "permissions": {"required": permissions, "optional": []},
                "status": status,
                "doc_path": f"/workspace/.weagent/tools/{capability_id}/TOOL.md",
            }
        )
        projection["agents"][agent_id]["permissions"]["grants"].append(
            {
                "binding_id": f"binding-{agent_id}-{source_ref}",
                "capability_id": capability_id,
                "capability_version_id": version_id,
                "capability_type": "tool",
                "granted_permissions": permissions,
            }
        )

    for item in TOOL_DEFS:
        add_tool(*item)
    add_tool("file_operations", "File Operations Limited", "workspace.files", ["read_file", "write_file", "list_files"], ["read_workspace"], LIMITED_AGENT_ID)
    add_tool("code_generator", "Code Generator Deferred", "code.generate", ["code_generator"], [], AGENT_ID, "deferred")
    return projection


class SmokeHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = json.dumps({"status": "ok", "path": self.path}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def start_http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    ensure_fixtures()
    projection = build_projection()
    write_projection(projection, workspace_root=str(WORKSPACE))
    write_run_snapshot(projection, RUN_ID, workspace_root=str(WORKSPACE))

    registry = ToolRegistry(workspace_root=str(WORKSPACE))
    register_builtin_tools(registry)

    calls = []

    def call(agent_id: str, tool_name: str, args: dict, expect_status: str = "ok"):
        payload = json.loads(
            registry.call_from_agent(
                agent_id,
                tool_name,
                args,
                run_id=RUN_ID,
                session_id=SESSION_ID,
            )
        )
        calls.append({"agent_id": agent_id, "tool": tool_name, "status": payload["status"]})
        require(payload["status"] == expect_status, f"{tool_name} returned {payload}")
        return payload.get("result")

    http_server = start_http_server()
    http_url = f"http://127.0.0.1:{http_server.server_port}/hello?token=redacted"

    try:
        require(call(AGENT_ID, "code_search", {"query": "TODO", "path": "src"})["matches"], "code_search found no matches")
        require(call(AGENT_ID, "code_review_scan", {"path": "src/sample.py"})["findings"], "code_review_scan found no findings")
        call(AGENT_ID, "write_file", {"path": "docs/generated.txt", "content": "generated by docker smoke"})
        require("generated by docker smoke" in call(AGENT_ID, "read_file", {"path": "docs/generated.txt"}), "read_file mismatch")
        require("docs/generated.txt" in call(AGENT_ID, "list_files", {"path": "docs"}), "list_files mismatch")
        require("UAT Note" in call(AGENT_ID, "document_text_extract", {"path": "docs/note.md"})["text"], "document extraction mismatch")
        require(call(AGENT_ID, "http_fetch", {"url": http_url})["status_code"] == 200, "http_fetch status mismatch")
        require(call(AGENT_ID, "api_request", {"url": http_url, "method": "GET"})["status_code"] == 200, "api_request status mismatch")
        require(call(AGENT_ID, "csv_profile", {"path": "data/sample.csv"})["row_count"] == 2, "csv_profile row count mismatch")
        require(call(AGENT_ID, "json_query", {"path": "data/sample.json", "query": "items.0.name"})["result"] == "alpha", "json_query mismatch")
        require(call(AGENT_ID, "sqlite_query_readonly", {"path": "data/sample.sqlite", "query": "SELECT name FROM items ORDER BY id"})["row_count"] == 2, "sqlite query mismatch")
        require(call(AGENT_ID, "image_info", {"path": "assets/pixel.png"})["width"] == 1, "image_info mismatch")
        require(call(AGENT_ID, "run_command_safe", {"command": "echo hello"})["stdout"].strip() == "hello", "run_command_safe mismatch")
        require(call(AGENT_ID, "git_status", {})["exit_code"] == 0, "git_status failed")
        require(call(AGENT_ID, "git_log", {"limit": 1})["exit_code"] == 0, "git_log failed")
        call(LIMITED_AGENT_ID, "write_file", {"path": "blocked.txt", "content": "blocked"}, expect_status="error")
        call(AGENT_ID, "code_generator", {}, expect_status="error")

        calls_path = WORKSPACE / ".weagent" / "runs" / RUN_ID / "calls.jsonl"
        records = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        require(any(item["status"] == "completed" for item in records), "no completed call records")
        require(any(item["status"] == "failed" for item in records), "no failed call records")
        require((WORKSPACE / ".weagent" / "agents" / AGENT_ID / "tool-index.json").exists(), "tool-index missing")
        require((WORKSPACE / ".weagent" / "tools" / "tool-code_search" / "TOOL.md").exists(), "TOOL.md missing")

        print(json.dumps({
            "status": "ok",
            "calls": calls,
            "record_count": len(records),
            "completed_records": sum(1 for item in records if item["status"] == "completed"),
            "failed_records": sum(1 for item in records if item["status"] == "failed"),
            "tool_index": f"/workspace/.weagent/agents/{AGENT_ID}/tool-index.json",
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        http_server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
