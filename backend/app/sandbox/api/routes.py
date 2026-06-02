"""
sandbox.api.routes — Host-side Flask blueprint for Docker-based sandbox.

Blueprint prefix: /api/sandbox

These endpoints call DockerContainerManager which talks to containers.
"""

import os
import re
from urllib.parse import quote

from flask import Blueprint, request, jsonify, Response

sandbox_bp = Blueprint("sandbox", __name__)

# Singleton manager
_manager = None


def _mgr():
    global _manager
    if _manager is None:
        from ..host.manager import DockerContainerManager
        _manager = DockerContainerManager()
    return _manager


# ============================
# Image management
# ============================


@sandbox_bp.route("/image/status", methods=["GET"])
def image_status():
    """Check if Docker image is built."""
    mgr = _mgr()
    ready = mgr.ensure_image()
    return jsonify({
        "code": 200,
        "data": {
            "ready": ready,
            "image": mgr.image_name,
        },
    })


@sandbox_bp.route("/image/build", methods=["POST"])
def build_image():
    """Build the Docker sandbox image."""
    try:
        import os
        mgr = _mgr()
        dockerfile_dir = os.path.join(os.path.dirname(__file__), "..")
        mgr.build_image(dockerfile_dir=dockerfile_dir)
        return jsonify({"code": 200, "message": "Image built"})
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


# ============================
# Session (容器) management
# ============================


@sandbox_bp.route("/sessions", methods=["POST"])
def create_session():
    """Create a new sandbox session (starts a Docker container).

    Body::

        {
          "session_id": "conv-001",
          "agents": [
            {"agent_id": "pm", "role": "产品经理", "system_prompt": "你负责需求分析..."},
            {"agent_id": "frontend", "role": "前端工程师", "system_prompt": "你负责实现..."}
          ]
        }
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id", f"session-{hash(str(data)) % 100000}")
    agents = data.get("agents", [])
    env_vars = data.get("env_vars")

    if not agents:
        return jsonify({"code": 400, "message": "At least one agent required"}), 400

    try:
        mgr = _mgr()
        session = mgr.create_session(session_id, agents, env_vars=env_vars)
        return jsonify({"code": 201, "data": session.to_dict()}), 201
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>", methods=["DELETE"])
def destroy_session(session_id: str):
    """Destroy a session (stop container)."""
    mgr = _mgr()
    mgr.destroy_session(session_id)
    return jsonify({"code": 200, "message": "Session destroyed"})


@sandbox_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get session details."""
    mgr = _mgr()
    session = mgr.get_session(session_id)
    if not session:
        return jsonify({"code": 404, "message": "Session not found"}), 404
    return jsonify({"code": 200, "data": session.to_dict()})


@sandbox_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List all active sessions."""
    mgr = _mgr()
    sessions = [s.to_dict() for s in mgr.list_sessions()]
    return jsonify({"code": 200, "data": sessions})


@sandbox_bp.route("/status", methods=["GET"])
def status():
    """Get manager status."""
    mgr = _mgr()
    return jsonify({"code": 200, "data": {
        **mgr.to_dict(),
        "sessions": [s.session_id for s in mgr.list_sessions()],
    }})


# ============================
# Agent communication
# ============================


@sandbox_bp.route("/sessions/<session_id>/send", methods=["POST"])
def send_message(session_id: str):
    """Send a message to an agent in a session.

    Body: {"agent_id": "pm", "message": "请写一个登录页面"}
    """
    data = request.get_json(force=True)
    agent_id = data.get("agent_id", "")
    message = data.get("message", "")

    if not message:
        return jsonify({"code": 400, "message": "message required"}), 400

    try:
        mgr = _mgr()
        if agent_id:
            result = mgr.send_message(session_id, agent_id, message)
        else:
            result = mgr.delegate_message(
                session_id,
                message,
                moderator_id=data.get("moderator_id", "moderator"),
                target_agent_ids=data.get("target_agent_ids"),
            )
        if result.get("status") == "error":
            return jsonify({
                "code": 400,
                "data": result,
                "message": result.get("error", "Agent execution failed"),
            }), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/chain", methods=["POST"])
def send_chain(session_id: str):
    """Chain: send message to agent1, feed output to agent2, etc.

    Body: {"messages": [{"agent_id": "pm", "message": "..."},
                        {"agent_id": "frontend", "message": "..."}]}
    """
    data = request.get_json(force=True)
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"code": 400, "message": "messages required"}), 400

    try:
        mgr = _mgr()
        results = mgr.send_chain(session_id, messages)
        return jsonify({"code": 200, "data": {"results": results}})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


# ============================
# Agent management within session
# ============================


@sandbox_bp.route("/sessions/<session_id>/agents", methods=["GET"])
def list_agents(session_id: str):
    """List agents in a session."""
    try:
        mgr = _mgr()
        info = mgr.get_session_info(session_id)
        return jsonify({"code": 200, "data": info})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/agents", methods=["POST"])
def add_agent(session_id: str):
    """Add an agent to an existing sandbox session."""
    data = request.get_json(force=True)
    agent_id = data.get("agent_id", "")
    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", agent_id):
        return jsonify({"code": 400, "message": "Invalid agent_id"}), 400

    config = {
        "agent_id": agent_id,
        "role": data.get("role", "助手"),
        "system_prompt": data.get("system_prompt", ""),
    }

    try:
        mgr = _mgr()
        result = mgr.add_agent(session_id, config)
        if "error" in result:
            return jsonify({"code": 400, "data": result, "message": result["error"]}), 400

        try:
            from app import socketio
            socketio.emit("sandbox_event", {
                "session_id": session_id,
                "agent_id": agent_id,
                "type": "agent_added",
                "data": {"agent": result.get("agent", config)},
                "seq": 0,
            }, room=session_id)
        except Exception:
            pass

        return jsonify({"code": 201, "data": result}), 201
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>", methods=["DELETE"])
def remove_agent(session_id: str, agent_id: str):
    """Remove an agent from an existing sandbox session."""
    try:
        mgr = _mgr()
        result = mgr.remove_agent(session_id, agent_id)
        if "error" in result:
            return jsonify({"code": 400, "data": result, "message": result["error"]}), 400

        try:
            from app import socketio
            socketio.emit("sandbox_event", {
                "session_id": session_id,
                "agent_id": agent_id,
                "type": "agent_removed",
                "data": {"agent_id": agent_id},
                "seq": 0,
            }, room=session_id)
        except Exception:
            pass

        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/history", methods=["GET"])
def agent_history(session_id: str, agent_id: str):
    """Get agent conversation history."""
    limit = request.args.get("limit", 0, type=int)
    try:
        mgr = _mgr()
        history = mgr.get_agent_history(session_id, agent_id, limit=limit)
        return jsonify({"code": 200, "data": history})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/files", methods=["GET"])
def read_agent_file(session_id: str, agent_id: str):
    """Read a file from the agent's container workspace.

    Query params:
        path: str — file path relative to /workspace
    """
    path = request.args.get("path", "")
    if not path:
        return jsonify({"code": 400, "message": "path query parameter required"}), 400
    mgr = _mgr()
    result = mgr.get_agent_file(session_id, agent_id, path)
    if "error" in result:
        return jsonify({"code": 404, "data": result}), 404
    return jsonify({"code": 200, "data": result})


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/files/raw", methods=["GET"])
def read_agent_raw_file(session_id: str, agent_id: str):
    """Serve raw file content with proper MIME type for browser rendering."""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"code": 400, "message": "path query parameter required"}), 400
    mgr = _mgr()
    try:
        content_bytes, mime_type = mgr.get_agent_raw_file(session_id, agent_id, path)
        return Response(content_bytes, mimetype=mime_type)
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "File not found"}), 404
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/files/tree", methods=["GET"])
def file_tree(session_id: str):
    """Return the session workspace file tree."""
    root = request.args.get("root", "/workspace")
    try:
        mgr = _mgr()
        result = mgr.get_file_tree(session_id, root=root)
        if "error" in result:
            return jsonify({"code": 400, "data": result, "message": result["error"]}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/files/raw", methods=["GET"])
def read_session_raw_file(session_id: str):
    """Serve raw workspace file content with proper MIME type."""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"code": 400, "message": "path query parameter required"}), 400
    try:
        mgr = _mgr()
        content_bytes, mime_type = mgr.get_raw_file(session_id, path)
        return Response(content_bytes, mimetype=mime_type)
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "File not found"}), 404
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/files/download", methods=["GET"])
def download_session_file(session_id: str):
    """Download a workspace file."""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"code": 400, "message": "path query parameter required"}), 400
    try:
        mgr = _mgr()
        content_bytes, mime_type, disposition = mgr.download_file(session_id, path)
        response = Response(content_bytes, mimetype=mime_type)
        if disposition:
            response.headers["Content-Disposition"] = disposition
        return response
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "File not found"}), 404
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/workspace/<path:filepath>", methods=["GET"])
def serve_workspace_file(session_id: str, filepath: str):
    """Serve a file from the container's /workspace/ with proper MIME type.

    This endpoint supports relative URL resolution so that HTML pages
    can reference CSS/JS/images via relative paths.

    Example:
      GET /api/sandbox/sessions/{sid}/workspace/index.html
      GET /api/sandbox/sessions/{sid}/workspace/css/style.css
    """
    mgr = _mgr()
    session = mgr.get_session(session_id)
    if not session:
        return jsonify({"code": 404, "message": "Session not found"}), 404

    # Pick the first agent (orchestrator read_file doesn't restrict by agent)
    agent_id = session.agents_config[0]["agent_id"] if session.agents_config else ""
    if not agent_id:
        return jsonify({"code": 400, "message": "No agents in session"}), 400

    try:
        workspace_path = f"/workspace/{filepath}"
        content_bytes, mime_type = mgr.get_agent_raw_file(session_id, agent_id, workspace_path)
        normalized_mime = (mime_type or "").split(";", 1)[0].strip().lower()
        if normalized_mime in {"text/html", "application/xhtml+xml"}:
            content_bytes = _inject_html_base(content_bytes, session_id, workspace_path)
        return Response(content_bytes, mimetype=mime_type)
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "File not found"}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


def _inject_html_base(content: bytes, session_id: str, workspace_path: str) -> bytes:
    """Inject base href so relative assets in generated HTML resolve via this API."""
    try:
        html = content.decode("utf-8")
    except UnicodeDecodeError:
        return content

    if re.search(r"<base\s", html, flags=re.IGNORECASE):
        return content

    rel_dir = os.path.dirname(workspace_path.replace("\\", "/"))
    if rel_dir.startswith("/workspace"):
        rel_dir = rel_dir[len("/workspace"):].lstrip("/")

    encoded_session = quote(session_id, safe="")
    encoded_dir = "/".join(quote(part, safe="") for part in rel_dir.split("/") if part)
    if encoded_dir:
        base_href = f"/api/sandbox/sessions/{encoded_session}/workspace/{encoded_dir}/"
    else:
        base_href = f"/api/sandbox/sessions/{encoded_session}/workspace/"

    base_tag = f'<base href="{base_href}">'
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        html = re.sub(r"(<head[^>]*>)", r"\1" + base_tag, html, count=1, flags=re.IGNORECASE)
    else:
        html = base_tag + html
    return html.encode("utf-8")


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/stop", methods=["POST"])
def stop_agent(session_id: str, agent_id: str):
    """Stop an agent's current execution."""
    mgr = _mgr()
    result = mgr.stop_agent(session_id, agent_id)
    if "error" in result:
        return jsonify({"code": 400, "data": result}), 400
    return jsonify({"code": 200, "data": result})


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/progress", methods=["GET"])
def agent_progress(session_id: str, agent_id: str):
    """Get agent's latest progress report (from volume file)."""
    mgr = _mgr()
    progress = mgr.get_agent_progress(session_id, agent_id)
    if not progress:
        return jsonify({"code": 200, "data": None})
    return jsonify({"code": 200, "data": progress})


@sandbox_bp.route("/sessions/<session_id>/agents/<agent_id>/events", methods=["GET"])
def agent_events(session_id: str, agent_id: str):
    """Get agent's execution events (event queue / progress log).

    Query params:
        since: int — only return events with seq > this value (default 0)
    """
    since = request.args.get("since", 0, type=int)
    mgr = _mgr()
    result = mgr.get_agent_events(session_id, agent_id, since=since)
    return jsonify({"code": 200, "data": result})


@sandbox_bp.route("/sessions/<session_id>/tools", methods=["GET"])
def list_custom_tools(session_id: str):
    try:
        result = _mgr().list_custom_tools(session_id)
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/tools", methods=["POST"])
def install_custom_tool(session_id: str):
    try:
        result = _mgr().install_tool(session_id, request.get_json(force=True))
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 201, "data": result}), 201
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/tools/<tool_name>", methods=["DELETE"])
def remove_custom_tool(session_id: str, tool_name: str):
    try:
        result = _mgr().remove_custom_tool(session_id, tool_name)
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/mcp/servers", methods=["GET"])
def list_mcp_servers(session_id: str):
    try:
        result = _mgr().list_mcp_servers(session_id)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/mcp/<runtime_id>/start", methods=["POST"])
def start_mcp_server(session_id: str, runtime_id: str):
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    if not agent_id:
        return jsonify({"code": 400, "message": "agent_id required"}), 400
    try:
        result = _mgr().start_mcp_server(session_id, agent_id, runtime_id)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/mcp/<runtime_id>/tools", methods=["GET"])
def list_mcp_tools(session_id: str, runtime_id: str):
    try:
        result = _mgr().list_mcp_tools(session_id, runtime_id)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/mcp/<runtime_id>/call", methods=["POST"])
def call_mcp_tool(session_id: str, runtime_id: str):
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    tool_name = data.get("tool_name", "")
    args = data.get("args") or {}
    if not agent_id:
        return jsonify({"code": 400, "message": "agent_id required"}), 400
    if not tool_name:
        return jsonify({"code": 400, "message": "tool_name required"}), 400
    try:
        result = _mgr().call_mcp_tool(session_id, agent_id, runtime_id, tool_name, args)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/mcp/<runtime_id>/stop", methods=["POST"])
def stop_mcp_server(session_id: str, runtime_id: str):
    try:
        result = _mgr().stop_mcp_server(session_id, runtime_id)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/services", methods=["GET"])
def list_services(session_id: str):
    try:
        result = _mgr().list_services(session_id)
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/services/start", methods=["POST"])
def start_service(session_id: str):
    try:
        result = _mgr().start_service(session_id, request.get_json(force=True))
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@sandbox_bp.route("/sessions/<session_id>/services/<int:port>/stop", methods=["POST"])
def stop_service(session_id: str, port: int):
    try:
        result = _mgr().stop_service(session_id, port)
        if result.get("status") == "error":
            return jsonify({"code": 400, "data": result, "message": result.get("error")}), 400
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/sessions/<session_id>/services/<int:port>/logs", methods=["GET"])
def service_logs(session_id: str, port: int):
    try:
        result = _mgr().service_logs(session_id, port)
        return jsonify({"code": 200, "data": result})
    except KeyError as e:
        return jsonify({"code": 404, "message": str(e)}), 404


@sandbox_bp.route("/events", methods=["POST"])
def container_event_callback():
    """Receive real-time events from containers and broadcast via SocketIO.

    Called by containers via HTTP POST (fire-and-forget).
    The container includes session_id so we can route to the right room.
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id", "")
    agent_id = data.get("agent_id", "")
    event_type = data.get("type", "")
    event_data = data.get("data", {})
    seq = data.get("seq", 0)
    print(
        f"[SandboxEvent] session={session_id} agent={agent_id} "
        f"type={event_type} seq={seq}"
    )

    if session_id:
        # Broadcast to all frontend clients in this session's room
        try:
            from app import socketio
            socketio.emit("sandbox_event", {
                "session_id": session_id,
                "agent_id": agent_id,
                "type": event_type,
                "data": event_data,
                "seq": seq,
            }, room=session_id)
            print(
                f"[SandboxEvent] socket_emit_ok session={session_id} "
                f"agent={agent_id} type={event_type} seq={seq}"
            )
        except Exception as e:
            print(
                f"[SandboxEvent] socket_emit_failed session={session_id} "
                f"agent={agent_id} type={event_type} seq={seq} error={e}"
            )

        try:
            from app.services.sandbox_event_bridge import sandbox_event_bridge
            sandbox_event_bridge.handle_event(data)
        except Exception as e:
            print(f"[WeAgent] Sandbox event bridge error: {e}")

    return jsonify({"code": 200})
