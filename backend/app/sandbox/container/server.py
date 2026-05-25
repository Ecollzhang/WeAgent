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

from flask import Flask, request, jsonify, Response

# Ensure container package is importable
sys.path.insert(0, "/app")

from container.orchestrator import Orchestrator
from container.events import get_events

app = Flask(__name__)
orchestrator = Orchestrator()


def _init_claude_settings():
    """Write .claude/settings.local.json from env vars at startup.

    This is needed because there's no host volume mount anymore —
    all config must be set up inside the container.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    model_name = os.environ.get("ANTHROPIC_MODEL", "")

    if api_key and base_url and model_name:
        settings = {
            "apiKey": api_key,  # top-level for our agent.py
            "baseURL": base_url,
            "model": model_name,
            "models": [
                {
                    "name": model_name,
                    "model": model_name,
                    "provider": "anthropic",
                    "apiKey": api_key,
                    "baseURL": base_url,
                }
            ],
            "permissions": {
                "allow": "all",
                "allowAlways": "all",
                "files": {
                    "allow": "all",
                    "read": True,
                    "write": True,
                    "delete": True,
                },
                "execute": {
                    "allow": True,
                },
            },
            "disableRestrictions": True,
        }
        claude_dir = "/workspace/.claude"
        os.makedirs(claude_dir, exist_ok=True)
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f, indent=2)
        print(f"[server] Wrote Claude settings (model={model_name})")


# Write Claude settings on import
_init_claude_settings()


# ============================
# Health
# ============================


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agents": len(orchestrator.agents)})


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

    if not agent_id:
        return jsonify({"status": "error", "error": "agent_id required"}), 400

    result = orchestrator.create_agent(agent_id, role, system_prompt, workspace_name)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def remove_agent(agent_id: str):
    result = orchestrator.remove_agent(agent_id)
    return jsonify(result)


@app.route("/api/agents/<agent_id>/stop", methods=["POST"])
def stop_agent(agent_id: str):
    """Stop an agent's current execution."""
    result = orchestrator.stop_agent(agent_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/agents", methods=["GET"])
def list_agents():
    return jsonify({"agents": orchestrator.list_agents()})


# ============================
# Messaging
# ============================


@app.route("/api/agents/<agent_id>/send", methods=["POST"])
def send_to_agent(agent_id: str):
    data = request.get_json(force=True)
    message = data.get("message", "")

    if not message:
        return jsonify({"status": "error", "error": "message required"}), 400

    result = orchestrator.send_to_agent(agent_id, message)
    if result.get("status") == "error":
        return jsonify(result), 400
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
        return jsonify({"status": "error", "error": "messages required"}), 400

    results = orchestrator.send_to_agent_chain(messages)
    return jsonify({"results": results})


@app.route("/api/agents/delegate", methods=["POST"])
def delegate_task():
    """Delegate a task via moderator when the user does not specify an agent."""
    data = request.get_json(force=True)
    message = data.get("message", "")
    moderator_id = data.get("moderator_id", "moderator")
    target_agent_ids = data.get("target_agent_ids")

    if not message:
        return jsonify({"status": "error", "error": "message required"}), 400

    result = orchestrator.delegate_task(
        message=message,
        moderator_id=moderator_id,
        target_agent_ids=target_agent_ids,
    )
    if result.get("status") == "error":
        return jsonify(result), 400
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
# Services
# ============================


@app.route("/api/services", methods=["GET"])
def list_services():
    return jsonify(orchestrator.list_services())


@app.route("/api/services/start", methods=["POST"])
def start_service():
    data = request.get_json(force=True)
    result = orchestrator.start_service(
        agent_id=data.get("agent_id", ""),
        command=data.get("command", ""),
        cwd=data.get("cwd", "/workspace"),
        port=int(data.get("port", 0)),
    )
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/services/<int:port>/stop", methods=["POST"])
def stop_service(port: int):
    result = orchestrator.stop_service(port)
    if result.get("status") == "error":
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/services/<int:port>/logs", methods=["GET"])
def service_logs(port: int):
    return jsonify(orchestrator.service_logs(port))


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
    return jsonify(orchestrator.get_session_info())


# ============================
# Main
# ============================

if __name__ == "__main__":
    port = int(os.environ.get("ORCHESTRATOR_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
