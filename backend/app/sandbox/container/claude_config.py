"""Claude Code non-interactive configuration helpers."""

import json
import os
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


PERMISSION_MODE = "bypassPermissions"

ALLOW_RULES = [
    "Read(*)",
    "Write(*)",
    "Edit(*)",
    "MultiEdit(*)",
    "Glob(*)",
    "Grep(*)",
    "LS(*)",
    "Bash(*)",
    "WebFetch(*)",
    "WebSearch(*)",
    "Task(*)",
    "TodoWrite(*)",
]


def clean_config_value(value: str = "") -> str:
    """Normalize values copied from JSON/env snippets before writing settings."""
    text = str(value or "").strip()
    text = text.strip(" \t\r\n'\"")
    return text


def clean_base_url(value: str = "") -> str:
    text = clean_config_value(value).rstrip("/")
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {text}")
    return text


def claude_env() -> dict:
    """Environment flags that keep Claude Code non-interactive in containers."""
    return {
        "CI": "1",
        "CLICOLOR": "0",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "CLAUDE_NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_PERMISSION_MODE": PERMISSION_MODE,
    }


def build_settings(api_key: str = "", base_url: str = "", model_name: str = "") -> dict:
    api_key = clean_config_value(api_key)
    base_url = clean_base_url(base_url)
    model_name = clean_config_value(model_name)

    settings = {
        "defaultMode": PERMISSION_MODE,
        "permissionMode": PERMISSION_MODE,
        "defaultPermissionMode": PERMISSION_MODE,
        "permissions": {
            "allow": ALLOW_RULES,
            "deny": [],
        },
        "disableRestrictions": True,
    }
    if api_key:
        settings["apiKey"] = api_key
    if base_url:
        settings["baseURL"] = base_url
    if model_name:
        settings["model"] = model_name
    if api_key or base_url or model_name:
        settings["models"] = [
            {
                "name": model_name,
                "model": model_name,
                "provider": "anthropic",
                "apiKey": api_key,
                "baseURL": base_url,
            }
        ]
    return settings


def write_settings(api_key: str = "", base_url: str = "", model_name: str = "") -> dict:
    settings = build_settings(api_key, base_url, model_name)
    for claude_dir in (Path("/workspace/.claude"), Path.home() / ".claude"):
        claude_dir.mkdir(parents=True, exist_ok=True)
        with (claude_dir / "settings.local.json").open("w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    return settings


def trust_projects(project_paths: Iterable[str]) -> None:
    """Pre-accept project trust/onboarding prompts for non-interactive runs."""
    config_path = Path.home() / ".claude.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        config = {}

    config.setdefault("hasCompletedOnboarding", True)
    config.setdefault("numStartups", 1)
    projects = config.setdefault("projects", {})

    for path in project_paths:
        normalized = os.path.abspath(path)
        project = projects.setdefault(normalized, {})
        project["hasTrustDialogAccepted"] = True
        project["projectOnboardingSeenCount"] = max(
            int(project.get("projectOnboardingSeenCount") or 0),
            1,
        )
        project.setdefault("allowedTools", ALLOW_RULES)
        project.setdefault("history", [])
        project.setdefault("mcpServers", {})
        project.setdefault("enabledMcpjsonServers", [])
        project.setdefault("disabledMcpjsonServers", [])

    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
