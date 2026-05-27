"""
container.events — Event queue for agent execution progress.

Each agent has a JSON Lines event file at /workspace/.session/events/{agent_id}.jsonl
for persistence. Additionally, events are pushed to the host via HTTP callback
for real-time delivery through SocketIO.

The host callback URL is read from the HOST_CALLBACK_URL env var,
set by DockerContainerManager when creating the container.
"""

import json
import os
import time
import urllib.request
import urllib.error

from .logging_utils import log_agent, log_event, shorten

EVENTS_DIR = "/workspace/.session/events"
HOST_URL = os.environ.get("HOST_CALLBACK_URL", "").rstrip("/")
SESSION_ID = os.environ.get("SESSION_ID", "")


def _ensure_dir():
    os.makedirs(EVENTS_DIR, exist_ok=True)


def _event_path(agent_id: str) -> str:
    return os.path.join(EVENTS_DIR, f"{agent_id}.jsonl")


def push_event(agent_id: str, event_type: str, data: dict) -> int:
    """Append an event (file + HTTP callback) and return its sequence number."""
    _ensure_dir()
    path = _event_path(agent_id)

    # Read current seq
    seq = 0
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ev = json.loads(line)
                        seq = ev.get("seq", 0)
                    except json.JSONDecodeError:
                        pass
    seq += 1

    event = {
        "seq": seq,
        "type": event_type,
        "agent_id": agent_id,
        "timestamp": time.time(),
        "data": data,
    }

    # Persist to file
    with open(path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    summary = _event_summary(event_type, data)
    log_agent(
        agent_id,
        "event_pushed",
        event_type=event_type,
        seq=seq,
        summary=summary,
    )

    # HTTP callback to host for real-time delivery
    _post_to_host(event)

    return seq


def _post_to_host(event: dict):
    """POST event to host's event endpoint (fire-and-forget)."""
    if not HOST_URL or not SESSION_ID:
        log_event(
            "event_callback_skipped",
            agent_id=event.get("agent_id", ""),
            event_type=event.get("type", ""),
            reason="missing HOST_CALLBACK_URL or SESSION_ID",
        )
        return

    payload = {
        "session_id": SESSION_ID,
        **event,  # agent_id, type, data, seq, timestamp
    }

    url = f"{HOST_URL}/api/sandbox/events"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Short timeout — fire and forget
        with urllib.request.urlopen(req, timeout=3) as resp:
            status = getattr(resp, "status", 0)
        log_event(
            "event_callback_ok",
            agent_id=event.get("agent_id", ""),
            event_type=event.get("type", ""),
            seq=event.get("seq", 0),
            status=status,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        log_event(
            "event_callback_failed",
            level="warning",
            agent_id=event.get("agent_id", ""),
            event_type=event.get("type", ""),
            seq=event.get("seq", 0),
            error=str(exc),
        )


def get_events(agent_id: str, since: int = 0) -> list[dict]:
    """Return all events with seq > since, newest first."""
    path = _event_path(agent_id)
    if not os.path.exists(path):
        return []

    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("seq", 0) > since:
                    events.append(ev)
            except json.JSONDecodeError:
                pass

    return events


def clear_events(agent_id: str):
    """Clear all events for an agent (e.g. on session destroy)."""
    path = _event_path(agent_id)
    if os.path.exists(path):
        os.remove(path)
        log_agent(agent_id, "events_cleared")


def _event_summary(event_type: str, data: dict) -> dict:
    data = data or {}
    if event_type in ("claude_output_delta", "claude_error_delta"):
        chunk = data.get("chunk", "")
        return {"chunk_len": len(chunk), "chunk_preview": shorten(chunk, 160)}
    if event_type in ("claude_output", "claude_error"):
        output = data.get("output", "")
        return {
            "output_len": len(output),
            "elapsed": data.get("elapsed"),
            "preview": shorten(output, 160),
        }
    if event_type == "agent_report_element":
        return {
            "report_type": data.get("type"),
            "status": data.get("status"),
            "title": (data.get("data") or {}).get("title"),
            "content_preview": shorten(data.get("content", ""), 160),
        }
    return {
        key: shorten(value, 160)
        for key, value in data.items()
        if key in ("message", "error", "file", "progress", "status", "role")
    }
