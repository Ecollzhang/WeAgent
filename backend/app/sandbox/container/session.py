"""
container.session — Session persistence for container-side orchestrator.

Stores/loads conversation history and agent config in /workspace/.session/
Data survives container restart because /workspace/ is a Docker volume.
"""

import json
import os
from datetime import datetime
from typing import Optional


SESSION_DIR = "/workspace/.session"
AGENTS_DIR = os.path.join(SESSION_DIR, "agents")
CONFIG_FILE = os.path.join(SESSION_DIR, "config.json")


def _ensure_dirs():
    os.makedirs(AGENTS_DIR, exist_ok=True)


def save_config(config: dict):
    """Save session-level config (agent list, roles, etc.)."""
    _ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_config() -> dict:
    """Load session-level config."""
    if not os.path.exists(CONFIG_FILE):
        return {"agents": []}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def agent_history_path(agent_id: str) -> str:
    return os.path.join(AGENTS_DIR, f"{agent_id}.jsonl")


def save_message(agent_id: str, role: str, content: str, metadata: Optional[dict] = None):
    """Append a message to agent's history."""
    _ensure_dirs()
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }
    if metadata:
        entry["metadata"] = metadata
    with open(agent_history_path(agent_id), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_history(agent_id: str, limit: int = 0) -> list[dict]:
    """Get full history for an agent. limit=0 means all."""
    path = agent_history_path(agent_id)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = f.readlines()
    if limit > 0:
        lines = lines[-limit:]
    return [json.loads(line) for line in lines]


def get_recent_context(agent_id: str, count: int = 5) -> str:
    """Get recent messages as formatted text (for context injection)."""
    history = get_history(agent_id, limit=count)
    parts = []
    for msg in history:
        parts.append(f"{msg['role']}: {msg['content']}")
    return "\n\n".join(parts)


def _normalize_adapter_name(adapter_name: str = "") -> str:
    return (adapter_name or "claude").strip().lower() or "claude"


def save_agent_config(agent_id: str, role: str, system_prompt: str,
                      workspace_name: str = "", adapter_name: str = "claude"):
    """Save agent config to session config."""
    config = load_config()
    agents = config.get("agents", [])
    adapter_name = _normalize_adapter_name(adapter_name)
    # Update if exists, else append
    for a in agents:
        if a["agent_id"] == agent_id:
            a.update({
                "role": role,
                "system_prompt": system_prompt,
                "workspace_name": workspace_name or role or agent_id,
                "adapter_name": adapter_name,
                "provider": adapter_name,
            })
            break
    else:
        agents.append({
            "agent_id": agent_id,
            "role": role,
            "system_prompt": system_prompt,
            "workspace_name": workspace_name or role or agent_id,
            "adapter_name": adapter_name,
            "provider": adapter_name,
        })
    config["agents"] = agents
    save_config(config)


def load_agent_config(agent_id: str) -> Optional[dict]:
    """Load a single agent's config."""
    config = load_config()
    for a in config.get("agents", []):
        if a["agent_id"] == agent_id:
            return a
    return None


def list_agents() -> list[dict]:
    """List all agents from config."""
    config = load_config()
    return config.get("agents", [])
