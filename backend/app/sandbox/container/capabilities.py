import json
import os
import re
import hashlib
from datetime import datetime


DEFAULT_WORKSPACE_ROOT = "/workspace"

BUILTIN_TOOL_RUNTIME_NAMES = {
    "file_operations": {"read_file", "write_file", "list_files"},
    "terminal": {"run_command"},
}

TOOL_PERMISSION_USAGE = {
    "read_file": ["read_workspace"],
    "list_files": ["read_workspace"],
    "write_file": ["write_workspace"],
    "run_command": ["run_command"],
}


def _safe_segment(value) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip())
    return text.strip(".-") or "item"


def _weagent_path(workspace_root: str, *parts: str) -> str:
    return os.path.join(workspace_root, ".weagent", *parts)


def _write_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content or "")


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _checksum_text(content: str) -> str:
    digest = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def agent_bootstrap_instruction(agent_id: str,
                                workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> str:
    safe_agent_id = _safe_segment(agent_id)
    base = f"{workspace_root}/.weagent/agents/{safe_agent_id}"
    return (
        "WeAgent capability runtime is available for this agent.\n"
        f"- Read capability bindings from {base}/capabilities.json\n"
        f"- Read available skills from {base}/skill-index.json\n"
        f"- Respect permission grants in {base}/permissions.json\n"
        "Only use capabilities listed in those files for this agent."
    )


def write_projection(projection: dict,
                     workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> dict:
    """Write a canonical session capability projection under .weagent/*."""
    projection = projection or {}
    index_path = _weagent_path(workspace_root, "capabilities", "index.json")
    _write_json(index_path, projection)
    written = [index_path]

    for capability_id, skill in (projection.get("skills") or {}).items():
        safe_id = _safe_segment(capability_id)
        skill_dir = _weagent_path(workspace_root, "skills", safe_id)
        skill_path = os.path.join(skill_dir, "SKILL.md")
        manifest_path = os.path.join(skill_dir, "manifest.json")
        _write_text(skill_path, skill.get("content", ""))
        baseline_content = skill.get("content", "")
        _write_json(manifest_path, {
            "capability_id": skill.get("capability_id") or capability_id,
            "version_id": skill.get("version_id"),
            "name": skill.get("name"),
            "description": skill.get("description", ""),
            "permissions": skill.get("permissions") or {},
            "manifest": skill.get("manifest") or {},
        })
        baseline_path = _weagent_path(
            workspace_root,
            "drafts",
            "skills",
            safe_id,
            "baseline.json",
        )
        _write_json(baseline_path, {
            "runtime_id": capability_id,
            "capability_id": skill.get("capability_id") or capability_id,
            "version_id": skill.get("version_id"),
            "name": skill.get("name"),
            "path": skill_path,
            "baseline_checksum": _checksum_text(baseline_content),
            "baseline_content": baseline_content,
            "last_draft_checksum": None,
        })
        written.extend([skill_path, manifest_path, baseline_path])

    for capability_id, record in (projection.get("mcp") or {}).items():
        safe_id = _safe_segment(capability_id)
        manifest_path = _weagent_path(workspace_root, "mcp", safe_id, "manifest.json")
        _write_json(manifest_path, {
            "capability_id": record.get("capability_id") or capability_id,
            "version_id": record.get("version_id"),
            "name": record.get("name"),
            "description": record.get("description", ""),
            "permissions": record.get("permissions") or {},
            "manifest": record.get("manifest") or {},
        })
        written.append(manifest_path)

    for capability_id, record in (projection.get("plugins") or {}).items():
        safe_id = _safe_segment(capability_id)
        manifest_path = _weagent_path(workspace_root, "plugins", safe_id, "manifest.json")
        _write_json(manifest_path, {
            "capability_id": record.get("capability_id") or capability_id,
            "version_id": record.get("version_id"),
            "name": record.get("name"),
            "description": record.get("description", ""),
            "permissions": record.get("permissions") or {},
            "manifest": record.get("manifest") or {},
        })
        written.append(manifest_path)

    for agent_id, view in (projection.get("agents") or {}).items():
        safe_agent_id = _safe_segment(agent_id)
        agent_dir = _weagent_path(workspace_root, "agents", safe_agent_id)
        capabilities_path = os.path.join(agent_dir, "capabilities.json")
        skill_index_path = os.path.join(agent_dir, "skill-index.json")
        permissions_path = os.path.join(agent_dir, "permissions.json")
        _write_json(capabilities_path, {
            "agent_id": view.get("agent_id") or agent_id,
            "capabilities": view.get("capabilities") or [],
            "files": view.get("files") or {},
            "bootstrap": view.get("bootstrap") or agent_bootstrap_instruction(agent_id),
        })
        _write_json(skill_index_path, {
            "agent_id": view.get("agent_id") or agent_id,
            "skills": view.get("skill_index") or [],
        })
        _write_json(permissions_path, view.get("permissions") or {
            "agent_id": view.get("agent_id") or agent_id,
            "grants": [],
        })
        written.extend([capabilities_path, skill_index_path, permissions_path])

    return {"status": "ok", "written": written}


def write_run_snapshot(projection: dict, run_id: str,
                       workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> dict:
    safe_run_id = _safe_segment(run_id)
    run_dir = _weagent_path(workspace_root, "runs", safe_run_id)
    snapshot_path = os.path.join(run_dir, "capability-snapshot.json")
    calls_path = os.path.join(run_dir, "calls.jsonl")
    _write_json(snapshot_path, projection or {})
    os.makedirs(run_dir, exist_ok=True)
    if not os.path.exists(calls_path):
        _write_text(calls_path, "")
    return {"status": "ok", "run_id": safe_run_id, "snapshot": snapshot_path, "calls": calls_path}


def collect_skill_draft_payloads(agent_id: str, session_id: str,
                                 workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> list[dict]:
    """Collect Agent-written runtime Skill changes as DB-syncable draft payloads."""
    agent_path = _weagent_path(
        workspace_root,
        "agents",
        _safe_segment(agent_id),
        "skill-index.json",
    )
    if not os.path.exists(agent_path):
        return []

    index = _read_json(agent_path)
    drafts = []
    for skill in index.get("skills") or []:
        runtime_id = skill.get("runtime_id") or skill.get("capability_id")
        if not runtime_id:
            continue
        safe_id = _safe_segment(runtime_id)
        baseline_path = _weagent_path(
            workspace_root,
            "drafts",
            "skills",
            safe_id,
            "baseline.json",
        )
        if not os.path.exists(baseline_path):
            continue
        baseline = _read_json(baseline_path)
        skill_path = baseline.get("path")
        if not skill_path or not os.path.exists(skill_path):
            continue
        current = _read_text(skill_path)
        current_checksum = _checksum_text(current)
        baseline_checksum = baseline.get("baseline_checksum")
        if current_checksum == baseline_checksum:
            baseline["last_draft_checksum"] = None
            _write_json(baseline_path, baseline)
            continue
        if current_checksum == baseline.get("last_draft_checksum"):
            continue

        payload = {
            "session_id": session_id,
            "agent_id": agent_id,
            "source_skill_id": baseline.get("capability_id") or skill.get("capability_id"),
            "source_version_id": baseline.get("version_id") or skill.get("version_id"),
            "runtime_id": runtime_id,
            "diff": {
                "changed": ["SKILL.md"],
                "path": skill_path,
                "old_checksum": baseline_checksum,
                "new_checksum": current_checksum,
                "old_length": len(baseline.get("baseline_content") or ""),
                "new_length": len(current),
            },
            "full_markdown": current,
        }
        draft_path = _weagent_path(
            workspace_root,
            "drafts",
            "skills",
            safe_id,
            f"{_safe_segment(agent_id)}.json",
        )
        _write_json(draft_path, payload)
        baseline["last_draft_checksum"] = current_checksum
        _write_json(baseline_path, baseline)
        drafts.append(payload)
    return drafts


def permissions_for_tool(tool_name: str) -> list[str]:
    return TOOL_PERMISSION_USAGE.get(tool_name, [])


def resolve_bound_tool_capability(agent_id: str, tool_name: str,
                                  workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> dict | None:
    """Find a Tool capability bound to this Agent that owns tool_name."""
    agent_path = _weagent_path(
        workspace_root,
        "agents",
        _safe_segment(agent_id),
        "capabilities.json",
    )
    if not os.path.exists(agent_path):
        return None

    view = _read_json(agent_path)
    for capability in view.get("capabilities") or []:
        if capability.get("type") != "tool":
            continue
        source_ref = capability.get("source_ref")
        manifest = capability.get("manifest") or {}
        if not source_ref:
            source_ref = (manifest.get("tool") or {}).get("value")
        runtime_names = set(capability.get("tool_names") or [])
        runtime_names.update(BUILTIN_TOOL_RUNTIME_NAMES.get(source_ref, set()))
        if not runtime_names and source_ref:
            runtime_names.add(source_ref)
        if tool_name not in runtime_names:
            continue
        return {
            "binding_id": capability.get("binding_id"),
            "capability_id": capability.get("capability_id"),
            "capability_version_id": capability.get("capability_version_id"),
            "runtime_id": capability.get("runtime_id"),
            "source_ref": source_ref,
            "granted_permissions": capability.get("granted_permissions") or [],
        }
    return None


def resolve_bound_mcp_capability(agent_id: str, runtime_id: str,
                                 workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> dict | None:
    """Find an MCP capability bound to this Agent by runtime id."""
    agent_path = _weagent_path(
        workspace_root,
        "agents",
        _safe_segment(agent_id),
        "capabilities.json",
    )
    if not os.path.exists(agent_path):
        return None

    view = _read_json(agent_path)
    for capability in view.get("capabilities") or []:
        if capability.get("type") != "mcp":
            continue
        candidate_ids = {
            capability.get("runtime_id"),
            capability.get("capability_id"),
            capability.get("id"),
        }
        if runtime_id not in candidate_ids:
            continue
        return {
            "binding_id": capability.get("binding_id"),
            "capability_id": capability.get("capability_id"),
            "capability_version_id": capability.get("capability_version_id"),
            "runtime_id": capability.get("runtime_id") or runtime_id,
            "source": capability.get("source"),
            "source_ref": capability.get("source_ref") or "",
            "granted_permissions": capability.get("granted_permissions") or [],
            "manifest": capability.get("manifest") or {},
        }
    return None


def summarize_tool_input(tool_name: str, args: dict) -> dict:
    args = args or {}
    if tool_name in {"read_file", "list_files"}:
        return {"path": args.get("path", "")}
    if tool_name == "write_file":
        return {
            "path": args.get("path", ""),
            "content_length": len(args.get("content") or ""),
        }
    if tool_name == "run_command":
        command = args.get("command", "")
        return {"command": command[:300], "command_length": len(command)}
    return {"arg_keys": sorted(args.keys())}


def summarize_mcp_input(tool_name: str, args: dict) -> dict:
    return {
        "tool_name": tool_name,
        "argument_keys": sorted((args or {}).keys()),
    }


def summarize_tool_output(result) -> dict:
    if isinstance(result, str):
        return {"text_length": len(result), "preview": result[:300]}
    if isinstance(result, dict):
        return {"keys": sorted(result.keys())}
    if isinstance(result, list):
        return {"items": len(result)}
    return {"type": type(result).__name__}


def summarize_mcp_output(result) -> dict:
    return summarize_tool_output(result)


def append_tool_call_record(record: dict, workspace_root: str = DEFAULT_WORKSPACE_ROOT):
    run_id = record.get("run_id")
    if not run_id:
        return
    calls_path = _weagent_path(
        workspace_root,
        "runs",
        _safe_segment(run_id),
        "calls.jsonl",
    )
    os.makedirs(os.path.dirname(calls_path), exist_ok=True)
    with open(calls_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.utcnow().isoformat()
