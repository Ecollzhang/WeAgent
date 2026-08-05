import json
import os
import re
import hashlib
from datetime import datetime


DEFAULT_WORKSPACE_ROOT = "/workspace"

BUILTIN_TOOL_RUNTIME_NAMES = {
    "code_search": {"code_search"},
    "code_review": {"code_review_scan"},
    "file_operations": {"read_file", "write_file", "list_files"},
    "document_parse": {"document_text_extract"},
    "web_fetch": {"http_fetch"},
    "api_client": {"api_request"},
    "web_search": {"web_search"},
    "data_analysis": {"csv_profile", "json_query", "sqlite_query_readonly"},
    "database_query": {"database_query"},
    "image_info": {"image_info"},
    "image_analysis": {"image_analysis"},
    "image_generation": {"image_generate"},
    "terminal": {"run_command_safe"},
    "git_operations": {"git_status", "git_diff", "git_log"},
    "rag_search": {"rag_search"},
    "education_actions": {"education_action"},
}

TOOL_PERMISSION_USAGE = {
    "read_file": ["read_workspace"],
    "list_files": ["read_workspace"],
    "write_file": ["write_workspace"],
    "document_text_extract": ["read_workspace"],
    "code_search": ["read_workspace"],
    "code_review_scan": ["read_workspace"],
    "run_command": ["run_command"],
    "run_command_safe": ["run_command"],
    "git_status": ["read_workspace"],
    "git_diff": ["read_workspace"],
    "git_log": ["read_workspace"],
    "http_fetch": ["network"],
    "api_request": ["network"],
    "web_search": ["network"],
    "csv_profile": ["read_workspace"],
    "json_query": ["read_workspace"],
    "sqlite_query_readonly": ["read_workspace"],
    "database_query": ["read_workspace", "use_secret"],
    "image_info": ["read_workspace"],
    "image_analysis": ["read_workspace"],
    "image_generate": ["write_workspace"],
    "rag_search": ["network"],
    "education_action": ["network"],
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


def _bundle_checksum(files: list[dict]) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda value: value.get("path") or ""):
        digest.update(str(item.get("path") or "").encode("utf-8"))
        digest.update(str(item.get("checksum") or "").encode("utf-8"))
        digest.update(str(bool(item.get("exists", True))).encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def _normalize_relative_path(path: str) -> str:
    normalized = str(path or "").replace("\\", "/").strip("/")
    if not normalized:
        return ""
    if re.match(r"^[a-zA-Z]:", normalized) or normalized.startswith("/"):
        raise ValueError(f"Unsafe capability asset path: {path}")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe capability asset path: {path}")
    return normalized


def _asset_file_records(skill: dict, skill_dir: str) -> list[dict]:
    records = []
    for asset in skill.get("assets") or []:
        rel_path = _normalize_relative_path(asset.get("path") or "")
        if not rel_path or rel_path == "SKILL.md":
            continue
        content = asset.get("content") or ""
        records.append({
            "path": rel_path,
            "absolute_path": os.path.join(skill_dir, *rel_path.split("/")),
            "kind": asset.get("kind") or "reference",
            "content": content,
            "checksum": asset.get("sha256") or _checksum_text(content),
            "mime_type": asset.get("mime_type") or "text/plain",
        })
    return sorted(records, key=lambda item: item["path"])


def _baseline_file_entry(path: str, absolute_path: str, kind: str,
                         content: str, mime_type: str = "text/plain") -> dict:
    return {
        "path": path,
        "absolute_path": absolute_path,
        "kind": kind,
        "checksum": _checksum_text(content),
        "content": content,
        "length": len(content or ""),
        "mime_type": mime_type,
        "exists": True,
    }


def agent_bootstrap_instruction(agent_id: str,
                                workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> str:
    safe_agent_id = _safe_segment(agent_id)
    base = f"{workspace_root}/.weagent/agents/{safe_agent_id}"
    return (
        "WeAgent capability runtime is available for this agent.\n"
        f"- Read capability bindings from {base}/capabilities.json\n"
        f"- Read available skills from {base}/skill-index.json\n"
        f"- Read available tools from {base}/tool-index.json\n"
        f"- Respect permission grants in {base}/permissions.json\n"
        "These JSON files are filesystem metadata, not MCP resources. Read them "
        "only with an ordinary filesystem tool when one is available; never call "
        "read_mcp_resource or invent an MCP server for their paths.\n"
        "When bound tools are exposed by the provider, invoke bound native tools "
        "directly from their supplied schema instead of probing for documentation.\n"
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
        asset_records = _asset_file_records(skill, skill_dir)
        for asset in asset_records:
            _write_text(asset["absolute_path"], asset["content"])
        baseline_files = [
            _baseline_file_entry(
                path="SKILL.md",
                absolute_path=skill_path,
                kind="skill_md",
                content=baseline_content,
            )
        ]
        baseline_files.extend(
            _baseline_file_entry(
                path=asset["path"],
                absolute_path=asset["absolute_path"],
                kind=asset["kind"],
                content=asset["content"],
                mime_type=asset["mime_type"],
            )
            for asset in asset_records
        )
        baseline_checksum = _bundle_checksum(baseline_files)
        _write_json(manifest_path, {
            "capability_id": skill.get("capability_id") or capability_id,
            "version_id": skill.get("version_id"),
            "name": skill.get("name"),
            "description": skill.get("description", ""),
            "permissions": skill.get("permissions") or {},
            "manifest": skill.get("manifest") or {},
            "assets": [
                {
                    "path": asset["path"],
                    "kind": asset["kind"],
                    "checksum": asset["checksum"],
                    "mime_type": asset["mime_type"],
                }
                for asset in asset_records
            ],
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
            "baseline_checksum": baseline_checksum,
            "baseline_content": baseline_content,
            "files": baseline_files,
            "last_draft_checksum": None,
        })
        written.extend([skill_path, manifest_path, baseline_path])
        written.extend(asset["absolute_path"] for asset in asset_records)

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

    for capability_id, record in (projection.get("tools") or {}).items():
        safe_id = _safe_segment(capability_id)
        tool_dir = _weagent_path(workspace_root, "tools", safe_id)
        doc_path = os.path.join(tool_dir, "TOOL.md")
        manifest_path = os.path.join(tool_dir, "manifest.json")
        _write_text(doc_path, record.get("content", ""))
        _write_json(manifest_path, {
            "capability_id": record.get("capability_id") or capability_id,
            "version_id": record.get("version_id"),
            "name": record.get("name"),
            "description": record.get("description", ""),
            "permissions": record.get("permissions") or {},
            "tool_names": record.get("tool_names") or [],
            "handler": record.get("handler") or "",
            "status": record.get("status") or "deferred",
            "provider_config": record.get("provider_config"),
            "manifest": record.get("manifest") or {},
        })
        written.extend([doc_path, manifest_path])

    for agent_id, view in (projection.get("agents") or {}).items():
        safe_agent_id = _safe_segment(agent_id)
        agent_dir = _weagent_path(workspace_root, "agents", safe_agent_id)
        capabilities_path = os.path.join(agent_dir, "capabilities.json")
        skill_index_path = os.path.join(agent_dir, "skill-index.json")
        tool_index_path = os.path.join(agent_dir, "tool-index.json")
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
        _write_json(tool_index_path, {
            "agent_id": view.get("agent_id") or agent_id,
            "tools": view.get("tool_index") or [],
        })
        _write_json(permissions_path, view.get("permissions") or {
            "agent_id": view.get("agent_id") or agent_id,
            "grants": [],
        })
        written.extend([capabilities_path, skill_index_path, tool_index_path, permissions_path])

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


def _baseline_files(baseline: dict) -> list[dict]:
    files = baseline.get("files")
    if files:
        return list(files)
    content = baseline.get("baseline_content") or ""
    return [
        {
            "path": "SKILL.md",
            "absolute_path": baseline.get("path"),
            "kind": "skill_md",
            "checksum": baseline.get("baseline_checksum") or _checksum_text(content),
            "content": content,
            "length": len(content),
            "mime_type": "text/plain",
            "exists": True,
        }
    ]


def _current_file_state(baseline_file: dict) -> dict:
    path = baseline_file.get("absolute_path")
    exists = bool(path and os.path.exists(path))
    content = _read_text(path) if exists else ""
    return {
        "path": baseline_file.get("path") or "",
        "absolute_path": path,
        "kind": baseline_file.get("kind") or "reference",
        "checksum": _checksum_text(content),
        "content": content,
        "length": len(content),
        "mime_type": baseline_file.get("mime_type") or "text/plain",
        "exists": exists,
    }


def _file_diff_entry(baseline_file: dict, current_file: dict) -> dict:
    if not current_file.get("exists", True):
        status = "deleted"
    elif not baseline_file.get("exists", True):
        status = "added"
    else:
        status = "modified"
    return {
        "path": current_file.get("path") or baseline_file.get("path") or "",
        "kind": current_file.get("kind") or baseline_file.get("kind") or "reference",
        "status": status,
        "old_checksum": baseline_file.get("checksum"),
        "new_checksum": current_file.get("checksum"),
        "old_length": baseline_file.get("length", len(baseline_file.get("content") or "")),
        "new_length": current_file.get("length", len(current_file.get("content") or "")),
    }


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
        baseline_files = _baseline_files(baseline)
        skill_file = next(
            (item for item in baseline_files if item.get("path") == "SKILL.md"),
            None,
        )
        skill_path = (skill_file or {}).get("absolute_path") or baseline.get("path")
        if not skill_path or not os.path.exists(skill_path):
            continue
        current_files = [_current_file_state(item) for item in baseline_files]
        current_skill = next(
            (item for item in current_files if item.get("path") == "SKILL.md"),
            None,
        )
        current = (current_skill or {}).get("content") or ""
        current_checksum = _bundle_checksum(current_files)
        baseline_checksum = baseline.get("baseline_checksum")
        if current_checksum == baseline_checksum:
            baseline["last_draft_checksum"] = None
            _write_json(baseline_path, baseline)
            continue
        if current_checksum == baseline.get("last_draft_checksum"):
            continue

        changed_files = [
            _file_diff_entry(original, current_state)
            for original, current_state in zip(baseline_files, current_files)
            if original.get("checksum") != current_state.get("checksum")
            or bool(original.get("exists", True)) != bool(current_state.get("exists", True))
        ]
        proposed_assets = [
            {
                "path": item["path"],
                "kind": item.get("kind") or "reference",
                "content": item.get("content") or "",
                "mime_type": item.get("mime_type") or "text/plain",
            }
            for item in current_files
            if item.get("path") != "SKILL.md" and item.get("exists", True)
        ]
        payload = {
            "session_id": session_id,
            "agent_id": agent_id,
            "source_skill_id": baseline.get("capability_id") or skill.get("capability_id"),
            "source_version_id": baseline.get("version_id") or skill.get("version_id"),
            "runtime_id": runtime_id,
            "diff": {
                "changed": [item["path"] for item in changed_files],
                "path": skill_path,
                "old_checksum": baseline_checksum,
                "new_checksum": current_checksum,
                "old_length": len(baseline.get("baseline_content") or ""),
                "new_length": len(current),
                "files": changed_files,
                "proposed_assets": proposed_assets,
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
        runtime_names.update(manifest.get("tool_names") or [])
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
            "status": (capability.get("status")
                       or (manifest.get("ui") or {}).get("status")
                       or "implemented"),
            "provider_config": capability.get("provider_config"),
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
    if tool_name in {
        "read_file",
        "list_files",
        "document_text_extract",
        "csv_profile",
        "json_query",
        "sqlite_query_readonly",
        "image_info",
        "code_review_scan",
    }:
        return {"path": args.get("path", "")}
    if tool_name == "code_search":
        return {
            "query": (args.get("query") or "")[:120],
            "path": args.get("path", ""),
            "max_results": args.get("max_results"),
        }
    if tool_name == "write_file":
        return {
            "path": args.get("path", ""),
            "content_length": len(args.get("content") or ""),
        }
    if tool_name in {"run_command", "run_command_safe"}:
        command = args.get("command", "")
        return {"command": command[:300], "command_length": len(command)}
    if tool_name in {"git_status", "git_diff", "git_log"}:
        return {"path": args.get("path", "")}
    if tool_name in {"http_fetch", "api_request"}:
        url = args.get("url", "")
        safe_url = str(url).split("?", 1)[0]
        return {"url": safe_url, "method": args.get("method", "GET")}
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
        summary = {"keys": sorted(result.keys())}
        if "matches" in result:
            summary["matches"] = len(result.get("matches") or [])
        if "findings" in result:
            summary["findings"] = len(result.get("findings") or [])
        if "row_count" in result:
            summary["row_count"] = result.get("row_count")
        if "status_code" in result:
            summary["status_code"] = result.get("status_code")
        if "exit_code" in result:
            summary["exit_code"] = result.get("exit_code")
        return summary
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
