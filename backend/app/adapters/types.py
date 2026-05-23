import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


AgentEvent = dict


@dataclass
class AgentRequest:
    prompt: str
    conversation_id: str | None = None
    agent_id: int | str | None = None
    agent_name: str | None = None
    system_prompt: str | None = None
    conversation_history: list | None = None
    workspace_path: str | Path | None = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict = field(default_factory=dict)


@dataclass
class AdapterHealth:
    provider: str
    available: bool
    detail: str = ""


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_workspace_path():
    workspace_root = os.getenv("AGENT_WORKSPACE_ROOT")
    if workspace_root:
        return Path(workspace_root).expanduser()
    return Path(__file__).resolve().parents[3]


def make_event(event_type, request, **payload):
    event = {
        "schemaVersion": "v1",
        "type": event_type,
        "runId": request.run_id,
        "conversationId": request.conversation_id,
        "agentId": request.agent_id,
        "agentName": request.agent_name,
        "timestamp": utc_now_iso(),
    }
    event.update(payload)
    return event
