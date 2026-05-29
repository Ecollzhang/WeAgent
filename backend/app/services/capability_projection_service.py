import re
from datetime import datetime

from app.models.capability import AgentCapabilityBinding


PROJECTION_SCHEMA_VERSION = "weagent.capability_projection/v1"
DEFAULT_WORKSPACE_ROOT = "/workspace"


def _safe_segment(value) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip())
    return text.strip(".-") or "item"


def _agent_files(agent_id: str, workspace_root: str) -> dict:
    safe_agent_id = _safe_segment(agent_id)
    base = f"{workspace_root}/.weagent/agents/{safe_agent_id}"
    return {
        "capabilities": f"{base}/capabilities.json",
        "skill_index": f"{base}/skill-index.json",
        "permissions": f"{base}/permissions.json",
    }


def _agent_bootstrap(agent_id: str, workspace_root: str) -> str:
    files = _agent_files(agent_id, workspace_root)
    return (
        "WeAgent capabilities for this agent are available in the canonical "
        f"runtime projection under {workspace_root}/.weagent.\n"
        f"- Capability view: {files['capabilities']}\n"
        f"- Skill index: {files['skill_index']}\n"
        f"- Permission grants: {files['permissions']}\n"
        "Use only capabilities listed in your agent view."
    )


def _version_dict(version) -> dict:
    return {
        "id": version.id,
        "version": version.version,
        "checksum": version.checksum,
        "manifest": version.manifest or {},
        "permissions": version.permissions or {"required": [], "optional": []},
        "meta": version.meta or {},
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def _runtime_id(binding: AgentCapabilityBinding, versions_by_capability: dict) -> str:
    version_ids = versions_by_capability.get(binding.capability_id) or set()
    if len(version_ids) <= 1:
        return binding.capability_id
    return f"{binding.capability_id}@{binding.capability_version_id}"


def _capability_record(binding: AgentCapabilityBinding, workspace_root: str,
                       runtime_id: str) -> dict:
    capability = binding.capability
    version = binding.capability_version
    record = {
        "runtime_id": runtime_id,
        "id": capability.id,
        "capability_id": capability.id,
        "type": capability.type,
        "name": capability.name,
        "slug": capability.slug,
        "description": capability.description or "",
        "source": capability.source,
        "source_ref": capability.source_ref or "",
        "is_builtin": bool(capability.is_builtin),
        "version": _version_dict(version),
    }
    if capability.type == "skill":
        record["path"] = f"{workspace_root}/.weagent/skills/{_safe_segment(runtime_id)}/SKILL.md"
    elif capability.type == "mcp":
        record["path"] = f"{workspace_root}/.weagent/mcp/{_safe_segment(runtime_id)}/manifest.json"
    elif capability.type == "plugin":
        record["path"] = f"{workspace_root}/.weagent/plugins/{_safe_segment(runtime_id)}/manifest.json"
    return record


def _skill_record(binding: AgentCapabilityBinding, workspace_root: str,
                  runtime_id: str) -> dict:
    capability = binding.capability
    version = binding.capability_version
    skill_base = f"{workspace_root}/.weagent/skills/{_safe_segment(runtime_id)}"
    return {
        "runtime_id": runtime_id,
        "capability_id": capability.id,
        "version_id": version.id,
        "name": capability.name,
        "description": capability.description or "",
        "content": version.content or "",
        "manifest": version.manifest or {},
        "permissions": version.permissions or {"required": [], "optional": []},
        "path": f"{skill_base}/SKILL.md",
        "manifest_path": f"{skill_base}/manifest.json",
    }


def _runtime_manifest_record(binding: AgentCapabilityBinding, workspace_root: str,
                             folder: str, runtime_id: str) -> dict:
    capability = binding.capability
    version = binding.capability_version
    return {
        "runtime_id": runtime_id,
        "capability_id": capability.id,
        "version_id": version.id,
        "name": capability.name,
        "description": capability.description or "",
        "manifest": version.manifest or {},
        "permissions": version.permissions or {"required": [], "optional": []},
        "path": f"{workspace_root}/.weagent/{folder}/{_safe_segment(runtime_id)}/manifest.json",
    }


def _tool_record(binding: AgentCapabilityBinding, runtime_id: str) -> dict:
    capability = binding.capability
    version = binding.capability_version
    return {
        "runtime_id": runtime_id,
        "capability_id": capability.id,
        "version_id": version.id,
        "name": capability.name,
        "description": capability.description or "",
        "source": capability.source,
        "source_ref": capability.source_ref or "",
        "manifest": version.manifest or {},
        "permissions": version.permissions or {"required": [], "optional": []},
    }


def _binding_view(binding: AgentCapabilityBinding, capability_record: dict) -> dict:
    return {
        "binding_id": binding.id,
        "capability_id": binding.capability_id,
        "capability_version_id": binding.capability_version_id,
        "type": capability_record["type"],
        "name": capability_record["name"],
        "version": capability_record["version"]["version"],
        "version_policy": binding.version_policy,
        "granted_permissions": binding.granted_permissions or [],
        "authorization_snapshot": binding.authorization_snapshot or {},
        "path": capability_record.get("path"),
        "runtime_id": capability_record["runtime_id"],
        "source": binding.capability.source,
        "source_ref": binding.capability.source_ref or "",
        "manifest": binding.capability_version.manifest or {},
    }


def _permission_grant(binding: AgentCapabilityBinding) -> dict:
    return {
        "binding_id": binding.id,
        "capability_id": binding.capability_id,
        "capability_version_id": binding.capability_version_id,
        "capability_type": binding.capability.type,
        "granted_permissions": binding.granted_permissions or [],
        "authorization_snapshot": binding.authorization_snapshot or {},
    }


def build_capability_projection(session_id: str, agents: list[dict],
                                workspace_root: str = DEFAULT_WORKSPACE_ROOT) -> dict:
    """Build the session-local capability projection from Agent bindings.

    The database remains canonical. The returned structure is safe to serialize
    into the session sandbox under /workspace/.weagent/*.
    """
    agent_configs = list(agents or [])
    agent_ids = [str(agent.get("agent_id")) for agent in agent_configs if agent.get("agent_id")]
    agent_order = {agent_id: index for index, agent_id in enumerate(agent_ids)}

    bindings = []
    if agent_ids:
        bindings = AgentCapabilityBinding.query.filter(
            AgentCapabilityBinding.agent_id.in_(agent_ids),
            AgentCapabilityBinding.enabled == True,  # noqa: E712
        ).all()
        bindings.sort(
            key=lambda item: (
                agent_order.get(item.agent_id, 10_000),
                item.capability.type,
                item.capability.name,
                item.id,
            )
        )
    versions_by_capability = {}
    for binding in bindings:
        versions_by_capability.setdefault(
            binding.capability_id, set()
        ).add(binding.capability_version_id)

    projection = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "session_id": session_id,
        "workspace_root": workspace_root,
        "generated_at": datetime.utcnow().isoformat(),
        "capabilities": {},
        "skills": {},
        "mcp": {},
        "plugins": {},
        "tools": {},
        "agents": {},
    }

    for agent_cfg in agent_configs:
        agent_id = str(agent_cfg.get("agent_id") or "")
        if not agent_id:
            continue
        projection["agents"][agent_id] = {
            "agent_id": agent_id,
            "role": agent_cfg.get("role") or agent_id,
            "capabilities": [],
            "skill_index": [],
            "permissions": {"agent_id": agent_id, "grants": []},
            "files": _agent_files(agent_id, workspace_root),
            "bootstrap": _agent_bootstrap(agent_id, workspace_root),
        }

    for binding in bindings:
        agent_view = projection["agents"].setdefault(
            binding.agent_id,
            {
                "agent_id": binding.agent_id,
                "role": binding.agent_id,
                "capabilities": [],
                "skill_index": [],
                "permissions": {"agent_id": binding.agent_id, "grants": []},
                "files": _agent_files(binding.agent_id, workspace_root),
                "bootstrap": _agent_bootstrap(binding.agent_id, workspace_root),
            },
        )
        capability = binding.capability
        runtime_id = _runtime_id(binding, versions_by_capability)
        capability_record = projection["capabilities"].get(runtime_id)
        if capability_record is None:
            capability_record = _capability_record(binding, workspace_root, runtime_id)
            projection["capabilities"][runtime_id] = capability_record
            if capability.type == "skill":
                projection["skills"][runtime_id] = _skill_record(
                    binding, workspace_root, runtime_id
                )
            elif capability.type == "mcp":
                projection["mcp"][runtime_id] = _runtime_manifest_record(
                    binding, workspace_root, "mcp", runtime_id
                )
            elif capability.type == "plugin":
                projection["plugins"][runtime_id] = _runtime_manifest_record(
                    binding, workspace_root, "plugins", runtime_id
                )
            elif capability.type == "tool":
                projection["tools"][runtime_id] = _tool_record(binding, runtime_id)

        agent_view["capabilities"].append(_binding_view(binding, capability_record))
        agent_view["permissions"]["grants"].append(_permission_grant(binding))
        if capability.type == "skill":
            agent_view["skill_index"].append({
                "capability_id": capability.id,
                "runtime_id": runtime_id,
                "version_id": binding.capability_version_id,
                "name": capability.name,
                "description": capability.description or "",
                "path": capability_record["path"],
            })

    return projection
