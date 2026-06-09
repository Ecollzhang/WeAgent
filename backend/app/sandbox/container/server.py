"""
container.server — Flask HTTP server that runs INSIDE the Docker container.

Listens on port 8080, receives commands from the host-side DockerManager,
and routes them to the Orchestrator.

Endpoints:
  POST /api/health                    — Health check
  POST /api/agents/create             — Create a new agent
  POST /api/agents/<id>/send          — Send message to agent
  POST /api/agents/chain              — Chain messages across agents
  DELETE /api/agents/<id>             — Remove an agent
  POST /api/agents/<id>/stop          — Stop an agent
  GET  /api/agents                    — List agents
  GET  /api/agents/<id>/history       — Get agent history
  GET  /api/agents/<id>/read_file     — Read a file from workspace
  GET  /api/tools                     — List tools
  POST /api/tools/execute             — Execute a tool
  GET  /api/session                   — Get session info
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, Response, g
import simple_websocket

# Ensure container package is importable
sys.path.insert(0, "/app")

from container.orchestrator import Orchestrator
from container.events import get_events
from container.claude_config import clean_base_url, clean_config_value, claude_env, write_settings, trust_projects
from container.logging_utils import configure_logging, log_agent, log_event, shorten
from container.provider_health import get_provider_health

app = Flask(__name__)
configure_logging()
orchestrator = Orchestrator()

_PROXY_BLOCKED_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
    "accept-encoding",
    "sec-websocket-key",
    "sec-websocket-version",
    "sec-websocket-extensions",
    "sec-websocket-protocol",
}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _filtered_proxy_headers(headers) -> dict:
    return {
        str(key): str(value)
        for key, value in dict(headers or {}).items()
        if str(key).lower() not in _PROXY_BLOCKED_HEADERS
    }


def _rewrite_service_location(location: str, service_id: str, port: int) -> str:
    if not location:
        return location
    proxy_prefix = f"/api/services/{service_id}/proxy"
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        if parsed.netloc in {f"127.0.0.1:{port}", f"localhost:{port}", f"0.0.0.0:{port}"}:
            suffix = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, parsed.fragment))
            return proxy_prefix + suffix
        return location
    if location.startswith("/"):
        return proxy_prefix + location
    return proxy_prefix + "/" + location


def _service_proxy_response(result: dict, service_id: str, port: int) -> Response:
    content_type = ""
    for key, value in result.get("headers", []) or []:
        if str(key).lower() == "content-type":
            content_type = str(value)
            break
    response = Response(
        result.get("body", b""),
        status=int(result.get("status_code") or 502),
        content_type=content_type or "application/octet-stream",
    )
    for key, value in result.get("headers", []) or []:
        header = str(key)
        if header.lower() in _PROXY_BLOCKED_HEADERS:
            continue
        if header.lower() == "content-type":
            continue
        if header.lower() == "location":
            value = _rewrite_service_location(str(value), service_id, port)
        response.headers.add(header, value)
    return response


def _is_websocket_request() -> bool:
    return request.headers.get("Upgrade", "").lower() == "websocket"


def _relay_websockets(left, right) -> dict:
    stop = threading.Event()

    def close_both():
        for ws in (left, right):
            try:
                ws.close()
            except Exception:
                pass

    def pump(source, target):
        while not stop.is_set():
            try:
                message = source.receive()
            except simple_websocket.ConnectionClosed:
                break
            except Exception:
                break
            if message is None:
                break
            try:
                target.send(message)
            except Exception:
                break
        stop.set()
        close_both()

    threads = [
        threading.Thread(target=pump, args=(left, right), daemon=True),
        threading.Thread(target=pump, args=(right, left), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"status": "closed"}


def _proxy_to_local_service_websocket(service_id: str, proxy_path: str):
    result = orchestrator.get_service(service_id)
    if result.get("error"):
        return Response(result["error"], status=404, content_type="text/plain; charset=utf-8")

    service = result.get("service") or {}
    port = int(service.get("port") or 0)
    if port <= 0:
        return Response("service has no valid port", status=502, content_type="text/plain; charset=utf-8")
    if service.get("status") in {"stopped", "failed", "exited"}:
        return Response(f"service is {service.get('status')}", status=502, content_type="text/plain; charset=utf-8")

    quoted_path = urllib.parse.quote(proxy_path or "", safe="/:@!$&'()*+,;=-._~")
    query_string = request.query_string.decode("utf-8", errors="ignore")
    url = f"ws://127.0.0.1:{port}/{quoted_path}"
    if query_string:
        url = f"{url}?{query_string}"

    client_ws = simple_websocket.Server.accept(request.environ)
    upstream_ws = simple_websocket.Client.connect(
        url,
        headers=_filtered_proxy_headers(request.headers),
    )
    _relay_websockets(client_ws, upstream_ws)
    return ""


def _proxy_to_local_service(service_id: str, proxy_path: str) -> tuple[dict, int | None]:
    result = orchestrator.get_service(service_id)
    if result.get("error"):
        return {
            "status_code": 404,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
            "body": result["error"].encode("utf-8"),
        }, None

    service = result.get("service") or {}
    port = int(service.get("port") or 0)
    if port <= 0:
        return {
            "status_code": 502,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
            "body": b"service has no valid port",
        }, None
    if service.get("status") in {"stopped", "failed", "exited"}:
        return {
            "status_code": 502,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
            "body": f"service is {service.get('status')}".encode("utf-8"),
        }, port

    quoted_path = urllib.parse.quote(proxy_path or "", safe="/:@!$&'()*+,;=-._~")
    query_string = request.query_string.decode("utf-8", errors="ignore")
    url = f"http://127.0.0.1:{port}/{quoted_path}"
    if query_string:
        url = f"{url}?{query_string}"

    body = request.get_data()
    data = body if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers=_filtered_proxy_headers(request.headers),
        method=request.method.upper(),
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)

    try:
        with opener.open(req, timeout=60) as resp:
            return {
                "status_code": resp.status,
                "headers": list(resp.headers.items()),
                "body": resp.read(),
            }, port
    except urllib.error.HTTPError as exc:
        return {
            "status_code": exc.code,
            "headers": list(exc.headers.items()),
            "body": exc.read(),
        }, port
    except urllib.error.URLError as exc:
        return {
            "status_code": 502,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
            "body": f"service proxy failed: {exc.reason}".encode("utf-8"),
        }, port


@app.before_request
def _log_request_start():
    g._request_start = time.time()


@app.after_request
def _log_request_done(response):
    started = getattr(g, "_request_start", None)
    elapsed_ms = round((time.time() - started) * 1000, 1) if started else None
    log_event(
        "api_request",
        method=request.method,
        path=request.path,
        status=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response


def _init_claude_settings():
    """Write .claude/settings.local.json from env vars at startup.

    This is needed because there's no host volume mount anymore —
    all config must be set up inside the container.
    """
    api_key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("DEEPSEEK_API_KEY")
        or ""
    )
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL") or ""
    model_name = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("DEEPSEEK_MODEL") or ""
    api_key = clean_config_value(api_key)
    base_url = clean_base_url(base_url)
    model_name = clean_config_value(model_name)

    os.environ.update(claude_env())
    write_settings(api_key, base_url, model_name)
    trust_projects(["/workspace"])
    log_event(
        "claude_settings_initialized",
        model=model_name or "env/default",
        base_url=base_url,
        has_api_key=bool(api_key),
    )


# Write Claude settings on import
_init_claude_settings()
PROVIDER_HEALTH = get_provider_health()
log_event("provider_health_initialized", providers=PROVIDER_HEALTH)


# ============================
# Health
# ============================


@app.route("/api/health", methods=["GET"])
def health():
    providers = PROVIDER_HEALTH
    log_event("api_health", agent_count=len(orchestrator.agents), providers=providers)
    return jsonify({"status": "ok", "agents": len(orchestrator.agents), "providers": providers})


@app.route("/api/providers", methods=["GET"])
def providers():
    refresh = request.args.get("refresh", "false").lower() == "true"
    health = get_provider_health() if refresh else PROVIDER_HEALTH
    log_event("api_providers", providers=health)
    return jsonify({"status": "ok", "providers": health})


# ============================
# Capability projection
# ============================


@app.route("/api/capabilities/projection", methods=["POST"])
def apply_capability_projection():
    data = request.get_json(force=True) or {}
    log_event(
        "api_capability_projection",
        agent_count=len((data.get("agents") or {}) if isinstance(data, dict) else {}),
        capability_count=len((data.get("capabilities") or {}) if isinstance(data, dict) else {}),
    )
    result = orchestrator.apply_capability_projection(data)
    if result.get("status") == "error" or "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/capabilities/drafts/collect", methods=["POST"])
def collect_skill_drafts():
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    drafts = orchestrator.collect_skill_drafts(agent_id)
    return jsonify({"status": "ok", "drafts": drafts})


# ============================
# Agent management
# ============================


@app.route("/api/agents/create", methods=["POST"])
def create_agent():
    data = request.get_json(force=True)
    agent_id = data.get("agent_id")
    role = data.get("role", "助手")
    system_prompt = data.get("system_prompt", "")
    workspace_name = data.get("workspace_name") or role or agent_id
    adapter_name = data.get("adapter_name") or data.get("provider") or "claude"

    if not agent_id:
        log_event("api_create_agent_rejected", level="warning", reason="agent_id required")
        return jsonify({"status": "error", "error": "agent_id required"}), 400

    log_agent(agent_id, "api_create_agent", role=role, workspace_name=workspace_name, adapter_name=adapter_name)
    result = orchestrator.create_agent(agent_id, role, system_prompt, workspace_name, adapter_name)
    if "error" in result:
        log_agent(agent_id, "api_create_agent_failed", level="error", error=result.get("error"))
        return jsonify(result), 400
    log_agent(agent_id, "api_create_agent_ok", role=role, workspace_name=result.get("agent", {}).get("workspace_name"))
    return jsonify(result), 201


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def remove_agent(agent_id: str):
    log_agent(agent_id, "api_remove_agent")
    result = orchestrator.remove_agent(agent_id)
    return jsonify(result)


@app.route("/api/agents/<agent_id>/stop", methods=["POST"])
def stop_agent(agent_id: str):
    """Stop an agent's current execution."""
    log_agent(agent_id, "api_stop_agent")
    result = orchestrator.stop_agent(agent_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/agents/<agent_id>/restart", methods=["POST"])
def restart_agent(agent_id: str):
    """Restart an agent runtime and restore recent context."""
    log_agent(agent_id, "api_restart_agent")
    result = orchestrator.restart_agent(agent_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/config/model", methods=["POST"])
def update_model_config():
    """Hot-update Claude Code config inside this container."""
    data = request.get_json(force=True) or {}
    log_event(
        "api_update_model_config",
        model=data.get("ANTHROPIC_MODEL") or data.get("model"),
        base_url=data.get("ANTHROPIC_BASE_URL") or data.get("baseURL"),
        has_api_key=bool(data.get("ANTHROPIC_API_KEY") or data.get("apiKey")),
    )
    result = orchestrator.update_model_config(data)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/agents", methods=["GET"])
def list_agents():
    log_event("api_list_agents", agent_count=len(orchestrator.agents))
    return jsonify({"agents": orchestrator.list_agents()})


# ============================
# Messaging
# ============================


@app.route("/api/agents/<agent_id>/send", methods=["POST"])
def send_to_agent(agent_id: str):
    data = request.get_json(force=True)
    message = data.get("message", "")

    if not message:
        log_agent(agent_id, "api_send_rejected", level="warning", reason="message required")
        return jsonify({"status": "error", "error": "message required"}), 400

    log_agent(agent_id, "api_send", message_len=len(message or ""), message_preview=shorten(message, 300))
    result = orchestrator.send_to_agent(agent_id, message)
    if result.get("status") == "error":
        log_agent(agent_id, "api_send_failed", level="error", error=result.get("error"))
        return jsonify(result), 400
    log_agent(agent_id, "api_send_ok", reply_len=len(result.get("reply", "") or ""), file_count=len(result.get("tool_results", []) or []))
    return jsonify(result)


@app.route("/api/agents/chain", methods=["POST"])
def send_chain():
    """Chain: send message to agent1, feed output to agent2, etc.

    Body: {"messages": [{"agent_id": "pm", "message": "..."},
                        {"agent_id": "frontend", "message": "..."}]}
    """
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    if not messages:
        log_event("api_chain_rejected", level="warning", reason="messages required")
        return jsonify({"status": "error", "error": "messages required"}), 400

    log_event("api_chain", message_count=len(messages), agents=[m.get("agent_id") for m in messages])
    results = orchestrator.send_to_agent_chain(messages)
    log_event("api_chain_ok", result_count=len(results))
    return jsonify({"results": results})


@app.route("/api/agents/delegate", methods=["POST"])
def delegate_task():
    """Delegate a task via moderator when the user does not specify an agent."""
    data = request.get_json(force=True)
    message = data.get("message", "")
    moderator_id = data.get("moderator_id", "moderator")
    target_agent_ids = data.get("target_agent_ids")

    if not message:
        log_agent(moderator_id, "api_delegate_rejected", level="warning", reason="message required")
        return jsonify({"status": "error", "error": "message required"}), 400

    log_agent(
        moderator_id,
        "api_delegate",
        message_len=len(message or ""),
        message_preview=shorten(message, 300),
        target_agent_ids=target_agent_ids,
    )
    result = orchestrator.delegate_task(
        message=message,
        moderator_id=moderator_id,
        target_agent_ids=target_agent_ids,
    )
    if result.get("status") == "error":
        log_agent(moderator_id, "api_delegate_failed", level="error", error=result.get("error"))
        return jsonify(result), 400
    log_agent(moderator_id, "api_delegate_ok", target_count=len(result.get("results", []) or []))
    return jsonify(result)


# ============================
# History
# ============================


@app.route("/api/agents/<agent_id>/history", methods=["GET"])
def agent_history(agent_id: str):
    limit = request.args.get("limit", 0, type=int)
    history = orchestrator.get_history(agent_id, limit=limit)
    return jsonify({"agent_id": agent_id, "count": len(history), "messages": history})


@app.route("/api/agents/<agent_id>/read_file", methods=["GET"])
def read_file(agent_id: str):
    """Read a file from the agent's workspace.

    Query params:
        path: str — file path (relative to /workspace or absolute)
    """
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "path query parameter required"}), 400
    result = orchestrator.read_file(agent_id, path)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/services/start", methods=["POST"])
def api_start_service():
    data = request.get_json() or {}
    required = ("cwd", "command", "port")
    missing = [key for key in required if not data.get(key)]
    if missing:
        return jsonify({"error": f"missing required fields: {', '.join(missing)}"}), 400
    result = orchestrator.start_service(data)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/services", methods=["GET"])
def api_list_preview_services():
    return jsonify(orchestrator.list_services())


@app.route("/api/services/<service_id>", methods=["GET"])
def api_get_preview_service(service_id: str):
    result = orchestrator.get_service(service_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/services/<service_id>/logs", methods=["GET"])
def api_get_preview_service_logs(service_id: str):
    try:
        tail_bytes = int(request.args.get("tail_bytes") or 65536)
    except ValueError:
        tail_bytes = 65536
    result = orchestrator.get_service_logs(service_id, tail_bytes=tail_bytes)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.route(
    "/api/services/<service_id>/proxy/",
    defaults={"proxy_path": ""},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@app.route(
    "/api/services/<service_id>/proxy/<path:proxy_path>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
def api_proxy_preview_service(service_id: str, proxy_path: str):
    if _is_websocket_request():
        return _proxy_to_local_service_websocket(service_id, proxy_path)
    result, port = _proxy_to_local_service(service_id, proxy_path)
    return _service_proxy_response(result, service_id, int(port or 0))


@app.route("/api/services/<service_id>/stop", methods=["POST"])
def api_stop_preview_service(service_id: str):
    result = orchestrator.stop_service(service_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/services/<service_id>/restart", methods=["POST"])
def api_restart_preview_service(service_id: str):
    result = orchestrator.restart_service(service_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/agents/<agent_id>/raw_file", methods=["GET"])
def raw_file(agent_id: str):
    """Return raw file content with proper MIME type for browser rendering.

    Query params:
        path: str — file path (relative to /workspace or absolute)
    """
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "path query parameter required"}), 400

    try:
        content, mime_type, _ = orchestrator.read_raw_file(path)
        return Response(content, mimetype=mime_type)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agents/<agent_id>/upload_file", methods=["POST"])
def upload_agent_file(agent_id: str):
    """Write uploaded bytes into the agent userInput directory."""
    path = request.form.get("path", "")
    file = request.files.get("file")
    if not path or not file:
        return jsonify({"error": "path and file required"}), 400
    result = orchestrator.write_binary_file(agent_id, path, file.read())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/agents/<agent_id>/delete_file", methods=["POST"])
def delete_agent_file(agent_id: str):
    """Delete an uploaded file from the agent userInput directory."""
    data = request.get_json(force=True)
    path = data.get("path", "")
    if not path:
        return jsonify({"error": "path required"}), 400
    result = orchestrator.delete_file(agent_id, path)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/files/tree", methods=["GET"])
def file_tree():
    """Return a tree of files under /workspace."""
    root = request.args.get("root", "/workspace")
    include_hidden = request.args.get("include_hidden", "false").lower() == "true"
    max_depth = request.args.get("max_depth", 8, type=int)
    result = orchestrator.list_tree(root=root, include_hidden=include_hidden, max_depth=max_depth)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/files/raw", methods=["GET"])
def session_raw_file():
    """Return raw workspace file content with proper MIME type."""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "path query parameter required"}), 400
    try:
        content, mime_type, _ = orchestrator.read_raw_file(path)
        return Response(content, mimetype=mime_type)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/files/download", methods=["GET"])
def download_file():
    """Download a workspace file as an attachment."""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "path query parameter required"}), 400
    try:
        content, mime_type, filename = orchestrator.read_raw_file(path)
        response = Response(content, mimetype=mime_type)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ============================
# Tools
# ============================


@app.route("/api/tools", methods=["GET"])
def list_tools():
    return jsonify({"tools": orchestrator.list_tools()})


@app.route("/api/tools/execute", methods=["POST"])
def execute_tool():
    data = request.get_json(force=True)
    agent_id = data.get("agent_id", "unknown")
    tool_name = data.get("tool_name", "")
    args = data.get("args", {})

    result = orchestrator.execute_tool(agent_id, tool_name, args)
    try:
        return jsonify({"status": "ok", "result": json.loads(result)})
    except (json.JSONDecodeError, TypeError):
        return jsonify({"status": "ok", "result": result})


# ============================
# MCP
# ============================


@app.route("/api/mcp/servers", methods=["GET"])
def list_mcp_servers():
    return jsonify(orchestrator.list_mcp_servers())


@app.route("/api/mcp/<runtime_id>/start", methods=["POST"])
def start_mcp_server(runtime_id: str):
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    if not agent_id:
        return jsonify({"status": "error", "error": "agent_id required"}), 400
    result = orchestrator.start_mcp_server(agent_id, runtime_id)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/mcp/<runtime_id>/tools", methods=["GET"])
def list_mcp_tools(runtime_id: str):
    result = orchestrator.list_mcp_tools(runtime_id)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/mcp/<runtime_id>/call", methods=["POST"])
def call_mcp_tool(runtime_id: str):
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    tool_name = data.get("tool_name", "")
    args = data.get("args") or {}
    if not agent_id:
        return jsonify({"status": "error", "error": "agent_id required"}), 400
    if not tool_name:
        return jsonify({"status": "error", "error": "tool_name required"}), 400
    result = orchestrator.call_mcp_tool(agent_id, runtime_id, tool_name, args)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/mcp/<runtime_id>/stop", methods=["POST"])
def stop_mcp_server(runtime_id: str):
    return jsonify(orchestrator.stop_mcp_server(runtime_id))


@app.route("/api/report", methods=["POST"])
def report_element():
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    report = data.get("report") or {}
    if not agent_id:
        log_event("api_report_rejected", level="warning", reason="agent_id required")
        return jsonify({"status": "error", "error": "agent_id required"}), 400
    log_agent(
        agent_id,
        "api_report",
        report_type=report.get("type") if isinstance(report, dict) else None,
        title=report.get("title") if isinstance(report, dict) else None,
        content_preview=shorten(report.get("content", ""), 200) if isinstance(report, dict) else "",
    )
    result = orchestrator.report_element(agent_id, report)
    if result.get("status") == "error":
        log_agent(agent_id, "api_report_failed", level="warning", error=result.get("error"))
        return jsonify({
            **result,
            "message": "WEAGENT_REPORT_VALIDATION_ERROR",
            "hint": "Fix the JSON passed to weagent-report and call it again. See error for valid examples.",
        }), 400
    log_agent(agent_id, "api_report_ok", report_type=result.get("element", {}).get("type"))
    return jsonify(result)


@app.route("/api/tools/install", methods=["POST"])
def install_tool():
    data = request.get_json(force=True)
    result = orchestrator.install_tool(data)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/tools/custom", methods=["GET"])
def custom_tools():
    return jsonify({"tools": orchestrator.list_custom_tools()})


@app.route("/api/tools/custom/<tool_name>", methods=["DELETE"])
def remove_custom_tool(tool_name: str):
    return jsonify(orchestrator.remove_custom_tool(tool_name))


# ============================
# Session
# ============================


@app.route("/api/agents/<agent_id>/progress", methods=["GET"])
def agent_progress(agent_id: str):
    """Read agent's progress report from workspace file."""
    progress_file = f"/workspace/.session/progress_{agent_id}.json"
    if not os.path.exists(progress_file):
        return jsonify({"progress": None})
    with open(progress_file) as f:
        return jsonify({"progress": json.load(f)})


@app.route("/api/agents/<agent_id>/events", methods=["GET"])
def agent_events(agent_id: str):
    """Get agent's execution events since a sequence number.

    Query params:
        since: int — only return events with seq > this value (default 0)
    """
    since = request.args.get("since", 0, type=int)
    events = get_events(agent_id, since=since)
    return jsonify({
        "agent_id": agent_id,
        "since": since,
        "count": len(events),
        "events": events,
    })


@app.route("/api/session", methods=["GET"])
def session_info():
    data = orchestrator.get_session_info()
    data["providers"] = PROVIDER_HEALTH
    return jsonify(data)


# ============================
# Main
# ============================

if __name__ == "__main__":
    port = int(os.environ.get("ORCHESTRATOR_PORT", 8080))
    log_event("server_starting", port=port)
    app.run(host="0.0.0.0", port=port, debug=False)
