import hashlib
import re
from datetime import datetime

from app import db
from app.models.agent import Agent
from app.models.capability import (
    CALL_STATUSES,
    AgentCapabilityBinding,
    Capability,
    CapabilityCallRecord,
    CapabilitySecurityAudit,
    CapabilityVersion,
    CapabilityVersionAsset,
    PluginInstallRecord,
    SkillRevisionDraft,
)


REQUIRED_PERMISSIONS = {
    "read_workspace",
    "write_workspace",
    "run_command",
    "network",
    "use_secret",
    "modify_skill",
    "start_service",
}


BUILTIN_MCP_CAPABILITIES = [
    {
        "type": "mcp",
        "name": "Memory MCP",
        "slug": "builtin-mcp-memory",
        "description": "Official MCP memory server for storing and retrieving structured entities.",
        "source": "builtin",
        "source_ref": "@modelcontextprotocol/server-memory",
        "category_id": "tool_data",
        "version": "1.0.0",
        "manifest": {
            "schema_version": "weagent.capability/v1",
            "source": {
                "type": "npx",
                "package": "@modelcontextprotocol/server-memory",
                "version": "latest",
            },
            "entry": {
                "command": "npx",
                "args": ["--yes", "@modelcontextprotocol/server-memory"],
            },
            "tools": [
                {"name": "create_entities", "description": "Create memory graph entities."},
                {"name": "create_relations", "description": "Create relations between entities."},
                {"name": "add_observations", "description": "Add observations to existing entities."},
                {"name": "delete_entities", "description": "Delete entities from the memory graph."},
                {"name": "delete_observations", "description": "Delete observations from entities."},
                {"name": "delete_relations", "description": "Delete relations from the memory graph."},
                {"name": "read_graph", "description": "Read the memory graph."},
                {"name": "search_nodes", "description": "Search stored memory nodes."},
                {"name": "open_nodes", "description": "Open specific memory graph nodes."},
            ],
        },
        "permissions": {"required": ["run_command"], "optional": []},
        "meta": {
            "seeded_from": "official_modelcontextprotocol_server",
            "uat_sample": True,
        },
    }
]


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return text or "capability"


def _normalize_permissions(permissions=None) -> dict:
    permissions = permissions or {}
    required = list(dict.fromkeys(permissions.get("required") or []))
    optional = list(dict.fromkeys(permissions.get("optional") or []))
    declared = set(required) | set(optional)
    unknown = declared - REQUIRED_PERMISSIONS
    if unknown:
        raise ValueError(f"Unknown permissions: {', '.join(sorted(unknown))}")
    return {"required": required, "optional": optional}


def _checksum(*parts) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part or "").encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def _asset_checksum(asset) -> str:
    digest = hashlib.sha256()
    digest.update(str(asset.get("content") or "").encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def _normalize_assets(assets=None) -> list[dict]:
    normalized = []
    for asset in assets or []:
        path = str(asset.get("path") or "").replace("\\", "/").strip("/")
        if not path:
            continue
        content = asset.get("content") or ""
        kind = asset.get("kind") or "reference"
        normalized.append({
            "path": path,
            "kind": kind,
            "content": content,
            "size": int(asset.get("size") or len(content.encode("utf-8"))),
            "sha256": asset.get("sha256") or _asset_checksum({"content": content}),
            "mime_type": asset.get("mime_type") or "text/plain",
            "meta": asset.get("meta") or {},
        })
    return sorted(normalized, key=lambda item: item["path"])


class CapabilityService:
    """Capability library and Agent binding business rules."""

    def list_capabilities(self, user_id, capability_type=None, category_id=None, domain=None):
        query = self._visible_capability_query(user_id)
        if capability_type:
            query = query.filter(Capability.type == capability_type)
        if category_id:
            query = query.filter(Capability.category_id == category_id)
        if domain:
            query = query.filter(Capability.domain == domain)
        records = query.order_by(Capability.created_at.desc()).all()
        return [self._capability_to_dict(record, user_id=user_id) for record in records], None

    def get_capability(self, user_id, capability_id):
        capability = self._visible_capability_query(user_id).filter(
            Capability.id == capability_id
        ).first()
        if not capability:
            return None, "Capability not found"
        return self._capability_to_dict(capability, include_latest=True, user_id=user_id), None

    def get_versions(self, user_id, capability_id):
        capability = self._visible_capability_query(user_id).filter(
            Capability.id == capability_id
        ).first()
        if not capability:
            return None, "Capability not found"
        versions = CapabilityVersion.query.filter_by(
            capability_id=capability.id
        ).order_by(CapabilityVersion.created_at.desc()).all()
        return [self._version_to_dict(version) for version in versions], None

    def create_skill(self, user_id, name, markdown, description="", permissions=None,
                     meta=None, source="user", source_ref="manual",
                     category_id=None, category_slug=None, assets=None):
        if not name or not str(name).strip():
            return None, "Capability name is required"
        if markdown is None:
            return None, "Skill markdown is required"

        try:
            resolved_category_id = self._resolve_category_id(
                user_id,
                category_id=category_id,
                category_slug=category_slug,
            )
        except ValueError as exc:
            return None, str(exc)

        capability = Capability(
            user_id=user_id,
            category_id=resolved_category_id,
            type="skill",
            name=name.strip(),
            slug=self._unique_slug(user_id, name),
            description=description or "",
            source=source,
            source_ref=source_ref or "",
            is_builtin=False,
        )
        db.session.add(capability)
        db.session.flush()

        version = self._make_version(
            capability=capability,
            version="1.0.0",
            content=markdown,
            manifest={"entry": "SKILL.md", "format": "markdown"},
            permissions=permissions,
            meta=meta,
            created_by=user_id,
            assets=assets,
        )
        capability.latest_version_id = version.id
        db.session.commit()
        return self._capability_to_dict(capability, include_latest=True), None

    def import_skill_markdown(self, user_id, markdown, source_ref="markdown",
                              category_id=None, category_slug=None):
        name = self._title_from_markdown(markdown) or "Imported Skill"
        return self.create_skill(
            user_id=user_id,
            name=name,
            markdown=markdown,
            source="markdown",
            source_ref=source_ref,
            meta={"imported": True},
            category_id=category_id,
            category_slug=category_slug,
        )

    def import_npx_manifest(self, user_id, manifest, source_ref="",
                            category_id=None, category_slug=None):
        if not isinstance(manifest, dict):
            return None, "Manifest must be an object"
        capabilities = manifest.get("capabilities") or []
        if not capabilities:
            return None, "Manifest contains no capabilities"

        source = manifest.get("source") or {}
        imported = []
        try:
            for item in capabilities:
                capability_type = item.get("type")
                if capability_type not in {"skill", "mcp", "plugin"}:
                    return None, f"Unsupported manifest capability type: {capability_type}"
                name = item.get("name") or "Imported Capability"
                permissions = _normalize_permissions(item.get("permissions"))
                item_category_id = self._resolve_category_id(
                    user_id,
                    category_id=item.get("category_id"),
                    category_slug=item.get("category") or item.get("category_slug"),
                ) if (
                    item.get("category_id") or item.get("category") or item.get("category_slug")
                ) else self._resolve_category_id(
                    user_id,
                    category_id=category_id,
                    category_slug=category_slug,
                )
                capability = Capability(
                    user_id=user_id,
                    category_id=item_category_id,
                    type=capability_type,
                    name=name,
                    slug=self._unique_slug(user_id, name),
                    description=item.get("description") or "",
                    source=source.get("type") or "npx",
                    source_ref=source_ref or source.get("package") or "",
                    is_builtin=False,
                )
                db.session.add(capability)
                db.session.flush()

                content = item.get("content") or ""
                if capability_type == "skill" and not content:
                    content = item.get("markdown") or f"# {name}\n"
                version = self._make_version(
                    capability=capability,
                    version=source.get("version") or item.get("version") or "1.0.0",
                    content=content,
                    manifest={
                        "schema_version": manifest.get("schema_version"),
                        "source": source,
                        "entry": item.get("entry"),
                        "tools": item.get("tools") or [],
                        "raw": item,
                    },
                    permissions=permissions,
                    meta={"imported_from": "npx_manifest"},
                    created_by=user_id,
                )
                capability.latest_version_id = version.id
                if capability_type == "plugin":
                    self._make_plugin_install_record(
                        user_id=user_id,
                        capability=capability,
                        version=version,
                        source=source,
                        source_ref=source_ref or source.get("package") or "",
                        manifest=manifest,
                        item=item,
                    )
                imported.append(capability)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            return None, str(exc)

        return [self._capability_to_dict(item, include_latest=True) for item in imported], None

    def import_mcp_manifest(self, user_id, manifest, source_ref="",
                            category_id=None, category_slug=None):
        if not isinstance(manifest, dict):
            return None, "Manifest must be an object"
        capabilities = manifest.get("capabilities") or []
        if not any(item.get("type") == "mcp" for item in capabilities):
            return None, "MCP manifest must include at least one MCP capability"
        if any(item.get("type") != "mcp" for item in capabilities):
            return None, "MCP manifest endpoint accepts only MCP capabilities"
        return self.import_npx_manifest(
            user_id=user_id,
            manifest=manifest,
            source_ref=source_ref,
            category_id=category_id,
            category_slug=category_slug,
        )

    def create_version(self, capability_id, content="", manifest=None, permissions=None,
                       meta=None, version=None, created_by=None, assets=None):
        capability = Capability.query.get(capability_id)
        if not capability:
            return None, "Capability not found"
        next_version = version or self._next_version(capability)
        try:
            version_record = self._make_version(
                capability=capability,
                version=next_version,
                content=content,
                manifest=manifest,
                permissions=permissions,
                meta=meta,
                created_by=created_by,
                assets=assets,
            )
        except ValueError as exc:
            return None, str(exc)

        capability.latest_version_id = version_record.id
        db.session.commit()
        return self._version_to_dict(version_record), None

    def create_user_version(self, user_id, capability_id, content="", manifest=None,
                            permissions=None, meta=None, version=None, assets=None):
        capability = self._visible_capability_query(user_id).filter(
            Capability.id == capability_id
        ).first()
        if not capability or (not capability.is_builtin and capability.user_id != user_id):
            return None, "Capability not found"
        if capability.is_builtin:
            return None, "Built-in capabilities cannot be edited"
        return self.create_version(
            capability_id=capability_id,
            content=content,
            manifest=manifest,
            permissions=permissions,
            meta=meta,
            version=version,
            created_by=user_id,
            assets=assets,
        )

    def bind_to_agent(self, agent_id, capability_version_id, granted_permissions=None,
                      version_policy="pinned", enabled=True):
        agent = Agent.query.get(agent_id)
        if not agent:
            return None, "Agent not found"
        return self._bind_to_agent(
            agent=agent,
            capability_version_id=capability_version_id,
            granted_permissions=granted_permissions,
            version_policy=version_policy,
            enabled=enabled,
            user_id=None,
        )

    def bind_to_user_agent(self, user_id, agent_id, capability_version_id, granted_permissions=None,
                           version_policy="pinned", enabled=True):
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, "Agent not found"
        return self._bind_to_agent(
            agent=agent,
            capability_version_id=capability_version_id,
            granted_permissions=granted_permissions,
            version_policy=version_policy,
            enabled=enabled,
            user_id=user_id,
        )

    def _bind_to_agent(self, agent, capability_version_id, granted_permissions=None,
                       version_policy="pinned", enabled=True, user_id=None):
        version = CapabilityVersion.query.get(capability_version_id)
        if not version:
            return None, "Capability version not found"
        if user_id is not None and not (
            version.capability.is_builtin or version.capability.user_id == user_id
        ):
            return None, "Capability version not found"
        if version_policy not in {"pinned", "follow_latest"}:
            return None, "Invalid version policy"
        if not self._is_capability_bindable(version.capability, version, user_id=user_id):
            ui = ((version.manifest or {}).get("ui") or {})
            if ui.get("status") == "requires_config" and ui.get("configurable"):
                return None, "Capability requires configuration before binding"
            return None, "Capability is not bindable"

        granted = list(dict.fromkeys(granted_permissions or []))
        declared = _normalize_permissions(version.permissions)
        granted_set = set(granted)
        allowed_set = set(declared["required"]) | set(declared["optional"])
        unknown_grants = granted_set - allowed_set
        if unknown_grants:
            return None, f"Granted permissions not declared: {', '.join(sorted(unknown_grants))}"
        missing = set(declared["required"]) - granted_set
        if missing:
            return None, f"Missing required permissions: {', '.join(sorted(missing))}"

        binding = AgentCapabilityBinding.query.filter_by(
            agent_id=agent.id,
            capability_id=version.capability_id,
        ).first()
        if not binding:
            binding = AgentCapabilityBinding(agent_id=agent.id, capability_id=version.capability_id)
            db.session.add(binding)

        binding.capability_version_id = version.id
        binding.enabled = enabled
        binding.version_policy = version_policy
        binding.granted_permissions = granted
        binding.authorization_snapshot = {
            "capability_id": version.capability_id,
            "capability_version_id": version.id,
            "capability_type": version.capability.type,
            "source": version.capability.source,
            "source_ref": version.capability.source_ref,
            "declared_permissions": declared,
            "granted_permissions": granted,
            "authorized_at": datetime.utcnow().isoformat(),
        }
        db.session.commit()
        return self._binding_to_dict(binding), None

    def get_agent_bindings(self, agent_id, user_id=None):
        if user_id is not None:
            agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
            if not agent:
                return None, "Agent not found"
        bindings = AgentCapabilityBinding.query.filter_by(agent_id=agent_id).all()
        return [self._binding_to_dict(binding) for binding in bindings], None

    def get_upgrade_status(self, agent_id):
        bindings = AgentCapabilityBinding.query.filter_by(agent_id=agent_id).all()
        result = []
        for binding in bindings:
            latest_id = binding.capability.latest_version_id
            if latest_id and latest_id != binding.capability_version_id:
                result.append({
                    "binding_id": binding.id,
                    "capability_id": binding.capability_id,
                    "current_version_id": binding.capability_version_id,
                    "latest_version_id": latest_id,
                    "upgrade_available": True,
                })
        return result, None

    def get_user_agent_upgrade_status(self, user_id, agent_id):
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, "Agent not found"
        return self.get_upgrade_status(agent_id)

    def update_user_agent_binding(self, user_id, agent_id, binding_id,
                                  capability_version_id=None, granted_permissions=None,
                                  version_policy="pinned", enabled=None):
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, "Agent not found"
        binding = AgentCapabilityBinding.query.filter_by(
            id=binding_id,
            agent_id=agent_id,
        ).first()
        if not binding:
            return None, "Agent capability binding not found"
        version_id = capability_version_id or binding.capability_version_id
        return self.bind_to_user_agent(
            user_id=user_id,
            agent_id=agent_id,
            capability_version_id=version_id,
            granted_permissions=granted_permissions
            if granted_permissions is not None else binding.granted_permissions,
            version_policy=version_policy or binding.version_policy,
            enabled=binding.enabled if enabled is None else enabled,
        )

    def list_drafts(self, user_id, status=None):
        query = self._draft_query(user_id)
        if status:
            query = query.filter(SkillRevisionDraft.status == status)
        drafts = query.order_by(SkillRevisionDraft.created_at.desc()).all()
        return [self._draft_to_dict(draft) for draft in drafts], None

    def publish_draft(self, user_id, draft_id, version=None,
                      override_confirmed=False, override_reason=""):
        draft = self._draft_query(user_id).filter(SkillRevisionDraft.id == draft_id).first()
        if not draft:
            return None, "Draft not found"
        if draft.status != "pending_review":
            return None, "Draft is not pending review"

        source_version = draft.source_version
        assets = self._draft_assets(draft, source_version)
        audit_files = self._draft_audit_files(draft, assets)
        from app.services.capability_security_audit_service import (
            capability_security_audit_service,
        )
        audit_record, audit_error = capability_security_audit_service.audit_and_record(
            user_id=user_id,
            files=audit_files,
            capability_id=draft.source_skill_id,
            draft_id=draft.id,
            override_confirmed=override_confirmed,
            override_reason=override_reason,
        )
        if audit_error:
            return None, audit_error
        version_result, error = self.create_version(
            capability_id=draft.source_skill_id,
            content=draft.full_markdown,
            manifest=source_version.manifest,
            permissions=source_version.permissions,
            meta={"published_from_draft": draft.id},
            version=version,
            created_by=user_id,
            assets=assets,
        )
        if error:
            return None, error

        if audit_record:
            audit = CapabilitySecurityAudit.query.get(audit_record["id"])
            if audit:
                audit.capability_version_id = version_result["id"]
        draft.status = "published"
        draft.reviewed_at = datetime.utcnow()
        db.session.commit()
        return {"draft": self._draft_to_dict(draft), "version": version_result}, None

    def fork_draft(self, user_id, draft_id, name=None):
        draft = self._draft_query(user_id).filter(SkillRevisionDraft.id == draft_id).first()
        if not draft:
            return None, "Draft not found"
        if draft.status != "pending_review":
            return None, "Draft is not pending review"

        capability_result, error = self.create_skill(
            user_id=user_id,
            name=name or f"{draft.source_skill.name} Fork",
            markdown=draft.full_markdown,
            description=f"Forked from {draft.source_skill.name}",
            permissions=draft.source_version.permissions,
            meta={"forked_from_draft": draft.id, "source_skill_id": draft.source_skill_id},
            source="user",
            source_ref=f"draft:{draft.id}",
            category_id=draft.source_skill.category_id,
            assets=self._draft_assets(draft, draft.source_version),
        )
        if error:
            return None, error

        draft.status = "forked"
        draft.reviewed_at = datetime.utcnow()
        db.session.commit()
        return {"draft": self._draft_to_dict(draft), "capability": capability_result}, None

    def sync_call_records(self, user_id, records):
        if not isinstance(records, list):
            return None, "Records must be a list"

        created = []
        for record in records:
            capability_id = record.get("capability_id")
            version_id = record.get("capability_version_id")
            agent_id = record.get("agent_id")
            if not capability_id or not version_id or not agent_id:
                return None, "Call record requires agent_id, capability_id, and capability_version_id"
            agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
            if not agent:
                return None, "Agent not found"
            capability = self._visible_capability_query(user_id).filter(
                Capability.id == capability_id
            ).first()
            version = CapabilityVersion.query.filter_by(
                id=version_id,
                capability_id=capability_id,
            ).first()
            if not capability or not version:
                return None, "Capability version not found"
            status = record.get("status") or "completed"
            if status not in CALL_STATUSES:
                return None, f"Invalid call status: {status}"

            call_record = CapabilityCallRecord(
                session_id=record.get("session_id") or "",
                run_id=record.get("run_id"),
                agent_id=agent_id,
                capability_id=capability_id,
                capability_version_id=version_id,
                call_type=record.get("call_type") or "tool",
                tool_name=record.get("tool_name") or "",
                permissions_used=record.get("permissions_used") or [],
                input_summary=record.get("input_summary") or {},
                output_summary=record.get("output_summary") or {},
                status=status,
                error=record.get("error"),
                started_at=self._parse_datetime(record.get("started_at")),
                completed_at=self._parse_datetime(record.get("completed_at")),
            )
            db.session.add(call_record)
            created.append(call_record)

        db.session.commit()
        return [self._call_record_to_dict(record) for record in created], None

    def list_call_records(self, user_id, session_id=None, agent_id=None):
        query = CapabilityCallRecord.query.join(
            Capability,
            CapabilityCallRecord.capability_id == Capability.id,
        ).filter((Capability.is_builtin == True) | (Capability.user_id == user_id))
        if session_id:
            query = query.filter(CapabilityCallRecord.session_id == session_id)
        if agent_id:
            query = query.filter(CapabilityCallRecord.agent_id == agent_id)
        records = query.order_by(CapabilityCallRecord.created_at.desc()).all()
        return [self._call_record_to_dict(record) for record in records], None

    def get_delete_impact(self, user_id, capability_id):
        capability = self._visible_capability_query(user_id).filter(
            Capability.id == capability_id
        ).first()
        if not capability:
            return None, "Capability not found"
        return self._delete_impact(capability, user_id), None

    def archive_user_capability(self, user_id, capability_id):
        capability = self._visible_capability_query(user_id).filter(
            Capability.id == capability_id
        ).first()
        if not capability:
            return None, "Capability not found"
        if capability.is_builtin:
            return None, "Built-in capabilities cannot be deleted"
        if capability.user_id != user_id:
            return None, "Capability not found"

        impact = self._delete_impact(capability, user_id)
        bindings = self._capability_bindings_for_user_agents(capability.id, user_id)
        for binding in bindings:
            db.session.delete(binding)

        if capability.type == "plugin":
            PluginInstallRecord.query.filter_by(
                user_id=user_id,
                plugin_capability_id=capability.id,
            ).update({"status": "removed"})

        capability.source = "archived"
        capability.slug = f"archived-{capability.id}-{capability.slug}"[:160]
        db.session.commit()

        impact["archived"] = True
        impact["removed_bindings"] = len(bindings)
        return impact, None

    def delete_user_agent_binding(self, user_id, agent_id, binding_id):
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, "Agent not found"
        binding = AgentCapabilityBinding.query.filter_by(
            id=binding_id,
            agent_id=agent_id,
        ).first()
        if not binding:
            return None, "Agent capability binding not found"
        db.session.delete(binding)
        db.session.commit()
        return {"deleted": True}, None

    def seed_builtin_tool_capabilities(self):
        from app.services.builtin_tool_definitions import get_builtin_tool_definitions
        from app.services.toolset_category_service import toolset_category_service

        toolset_category_service.seed_builtin_categories()

        for tool in get_builtin_tool_definitions():
            source_ref = tool["value"]
            category_id = self._resolve_category_id(
                None,
                category_id=tool.get("category"),
            )
            source = "hidden" if tool.get("visibility") == "hidden" else "builtin"
            existing = Capability.query.filter_by(
                type="tool",
                source_ref=source_ref,
                is_builtin=True,
            ).first()
            if existing:
                existing.category_id = category_id
                existing.name = tool["name"]
                existing.description = tool.get("description") or ""
                existing.source = source
                existing.domain = (
                    "edu"
                    if source_ref == "education_actions"
                    else (
                        "common"
                        if source_ref
                        in {"list_services", "call_service_api", "rag_search"}
                        else "rd"
                    )
                )
                latest = (
                    CapabilityVersion.query.get(existing.latest_version_id)
                    if existing.latest_version_id else None
                )
                desired_permissions = self._builtin_tool_permissions(source_ref)
                desired_manifest = tool["manifest"]
                desired_content = tool["markdown"]
                if (
                    not latest
                    or (latest.manifest or {}) != desired_manifest
                    or (latest.permissions or {}) != desired_permissions
                    or (latest.content or "") != desired_content
                ):
                    version = self._make_version(
                        capability=existing,
                        version=self._next_version(existing),
                        content=desired_content,
                        manifest=desired_manifest,
                        permissions=desired_permissions,
                        meta={"seeded_from": "builtin_tool_definitions"},
                    )
                    existing.latest_version_id = version.id
                continue
            capability = Capability(
                category_id=category_id,
                type="tool",
                name=tool["name"],
                slug=f"builtin-{_slugify(source_ref)}",
                description=tool.get("description") or "",
                source=source,
                source_ref=source_ref,
                is_builtin=True,
                domain=(
                    "edu"
                    if source_ref == "education_actions"
                    else (
                        "common"
                        if source_ref
                        in {"list_services", "call_service_api", "rag_search"}
                        else "rd"
                    )
                ),
            )
            db.session.add(capability)
            db.session.flush()
            version = self._make_version(
                capability=capability,
                version="1.0.0",
                content=tool["markdown"],
                manifest=tool["manifest"],
                permissions=self._builtin_tool_permissions(source_ref),
                meta={"seeded_from": "builtin_tool_definitions"},
            )
            capability.latest_version_id = version.id
        self._seed_builtin_mcp_capabilities()
        db.session.commit()

    def seed_education_agent_tool_bindings(self):
        """Bind guarded Education and common service tools by Agent manifest."""
        all_edu_agents = [f"_edu_{index}" for index in range(1, 10)]
        targets = {
            "education_actions": all_edu_agents,
            "list_services": all_edu_agents,
            "call_service_api": all_edu_agents,
            "rag_search": ["_edu_1", "_edu_2", "_edu_3", "_edu_7", "_edu_8"],
        }
        for source_ref, agent_ids in targets.items():
            capability = Capability.query.filter_by(
                type="tool",
                source_ref=source_ref,
                is_builtin=True,
            ).first()
            if not capability or not capability.latest_version_id:
                continue
            version = CapabilityVersion.query.get(capability.latest_version_id)
            if not version:
                continue
            declared = _normalize_permissions(version.permissions)
            granted = list(declared["required"])
            for agent_id in agent_ids:
                agent = Agent.query.get(agent_id)
                if not agent:
                    continue
                binding = AgentCapabilityBinding.query.filter_by(
                    agent_id=agent.id,
                    capability_id=capability.id,
                ).first()
                if not binding:
                    binding = AgentCapabilityBinding(
                        agent_id=agent.id,
                        capability_id=capability.id,
                    )
                    db.session.add(binding)
                binding.capability_version_id = version.id
                binding.enabled = True
                binding.version_policy = "follow_latest"
                binding.granted_permissions = granted
                binding.authorization_snapshot = {
                    "capability_id": capability.id,
                    "capability_version_id": version.id,
                    "capability_type": capability.type,
                    "source": capability.source,
                    "source_ref": capability.source_ref,
                    "declared_permissions": declared,
                    "granted_permissions": granted,
                    "scope": (
                        "server_issued_education_run_grant"
                        if source_ref == "education_actions"
                        else "agent_service_view"
                    ),
                    "authorized_at": datetime.utcnow().isoformat(),
                }
        db.session.commit()

    def _seed_builtin_mcp_capabilities(self):
        for item in BUILTIN_MCP_CAPABILITIES:
            category_id = self._resolve_category_id(
                None,
                category_id=item.get("category_id"),
            )
            existing = Capability.query.filter_by(
                type=item["type"],
                source=item["source"],
                source_ref=item["source_ref"],
                is_builtin=True,
            ).first()
            if existing:
                existing.category_id = category_id
                existing.description = item["description"]
                latest = (
                    CapabilityVersion.query.get(existing.latest_version_id)
                    if existing.latest_version_id else None
                )
                if (
                    not latest
                    or (latest.manifest or {}) != item["manifest"]
                    or (latest.permissions or {}) != item["permissions"]
                ):
                    version = self._make_version(
                        capability=existing,
                        version=self._next_version(existing),
                        manifest=item["manifest"],
                        permissions=item["permissions"],
                        meta=item["meta"],
                    )
                    existing.latest_version_id = version.id
                continue
            capability = Capability(
                category_id=category_id,
                type=item["type"],
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                source=item["source"],
                source_ref=item["source_ref"],
                is_builtin=True,
            )
            db.session.add(capability)
            db.session.flush()
            version = self._make_version(
                capability=capability,
                version=item["version"],
                manifest=item["manifest"],
                permissions=item["permissions"],
                meta=item["meta"],
            )
            capability.latest_version_id = version.id

    def _resolve_category_id(self, user_id, category_id=None, category_slug=None):
        from app.services.toolset_category_service import toolset_category_service

        return toolset_category_service.resolve_category_id(
            user_id,
            category_id=category_id,
            category_slug=category_slug,
        )

    def _make_version(self, capability, version, content="", manifest=None,
                      permissions=None, meta=None, created_by=None, assets=None):
        normalized_permissions = (
            permissions if permissions and "required" in permissions else _normalize_permissions(permissions)
        )
        if permissions and "required" in permissions:
            normalized_permissions = _normalize_permissions(permissions)
        normalized_assets = _normalize_assets(assets)
        version_record = CapabilityVersion(
            capability=capability,
            version=version,
            content=content or "",
            manifest=manifest or {},
            permissions=normalized_permissions,
            meta=meta or {},
            checksum=_checksum(content, manifest, normalized_permissions, meta, normalized_assets),
            created_by=created_by,
        )
        db.session.add(version_record)
        db.session.flush()
        for asset in normalized_assets:
            db.session.add(CapabilityVersionAsset(
                capability_version_id=version_record.id,
                path=asset["path"],
                kind=asset["kind"],
                content=asset["content"],
                size=asset["size"],
                sha256=asset["sha256"],
                mime_type=asset["mime_type"],
                meta=asset["meta"],
            ))
        if normalized_assets:
            db.session.flush()
        return version_record

    def _make_plugin_install_record(self, user_id, capability, version, source,
                                    source_ref, manifest, item):
        included_capabilities = (
            item.get("included_capabilities")
            or item.get("includes")
            or item.get("capabilities")
            or []
        )
        record = PluginInstallRecord(
            user_id=user_id,
            plugin_capability_id=capability.id,
            plugin_version_id=version.id,
            source=source.get("type") or capability.source or "npx",
            source_ref=source_ref or capability.source_ref or "",
            package_name=source.get("package") or "",
            package_version=source.get("version") or version.version or "",
            status="installed",
            manifest={
                "schema_version": manifest.get("schema_version"),
                "source": source,
                "plugin": item,
            },
            included_capabilities=included_capabilities,
        )
        db.session.add(record)
        db.session.flush()
        return record

    def _visible_capability_query(self, user_id):
        return Capability.query.filter(
            ((Capability.is_builtin == True) | (Capability.user_id == user_id)),
            ~Capability.source.in_(["archived", "hidden"]),
        )

    def _draft_query(self, user_id):
        return SkillRevisionDraft.query.join(
            Capability,
            SkillRevisionDraft.source_skill_id == Capability.id,
        ).filter((Capability.is_builtin == True) | (Capability.user_id == user_id))

    def _draft_assets(self, draft, source_version):
        diff = draft.diff or {}
        if "proposed_assets" in diff:
            return diff.get("proposed_assets") or []
        assets = []
        for asset in source_version.assets or []:
            path = str(asset.path or "").replace("\\", "/").strip("/")
            if not path or path == "SKILL.md":
                continue
            assets.append({
                "path": path,
                "kind": asset.kind,
                "content": asset.content or "",
                "size": asset.size,
                "sha256": asset.sha256,
                "mime_type": asset.mime_type or "text/plain",
                "meta": asset.meta or {},
            })
        return assets

    def _draft_audit_files(self, draft, assets):
        files = [{
            "path": "SKILL.md",
            "kind": "skill_md",
            "content": draft.full_markdown or "",
            "size": len((draft.full_markdown or "").encode("utf-8")),
        }]
        for asset in assets or []:
            content = asset.get("content") or ""
            files.append({
                "path": asset.get("path") or "",
                "kind": asset.get("kind") or "reference",
                "content": content,
                "size": asset.get("size") or len(content.encode("utf-8")),
                "mime_type": asset.get("mime_type") or "text/plain",
            })
        return files

    def _parse_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _builtin_tool_permissions(self, tool_value):
        from app.services.builtin_tool_definitions import get_builtin_tool_definition

        definition = get_builtin_tool_definition(tool_value)
        if definition:
            return definition["permissions"]
        return {"required": [], "optional": []}

    def _unique_slug(self, user_id, name):
        base = _slugify(name)
        slug = base
        suffix = 2
        while Capability.query.filter_by(user_id=user_id, slug=slug).first():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    def _next_version(self, capability):
        count = CapabilityVersion.query.filter_by(capability_id=capability.id).count()
        return f"1.0.{count}"

    def _title_from_markdown(self, markdown):
        for line in (markdown or "").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def _capability_to_dict(self, capability, include_latest=True, user_id=None):
        data = capability.to_dict()
        data["category"] = capability.category.to_dict() if capability.category else None
        latest = None
        if include_latest:
            if capability.latest_version_id:
                latest = CapabilityVersion.query.get(capability.latest_version_id)
            elif capability.versions:
                latest = capability.versions[-1]
            data["latest_version"] = self._version_to_dict(latest) if latest else None
        elif capability.latest_version_id:
            latest = CapabilityVersion.query.get(capability.latest_version_id)
        if capability.type == "tool":
            data.update(self._tool_catalog_state(capability, latest, user_id=user_id))
        if capability.type == "plugin":
            data["install_record"] = self._latest_plugin_install_record(capability)
        return data

    def _tool_catalog_state(self, capability, version=None, user_id=None):
        manifest = (version.manifest if version else {}) or {}
        ui = manifest.get("ui") or {}
        status = ui.get("status") or "deferred"
        visibility = ui.get("visibility") or (
            "hidden" if capability.source == "hidden" else "visible"
        )
        configurable = bool(ui.get("configurable"))
        configured_profiles_count = (
            self._valid_tool_provider_config_count(user_id, capability.id)
            if configurable else 0
        )
        bindable = self._is_capability_bindable(capability, version, user_id=user_id)
        return {
            "tool_status": status,
            "visibility": visibility,
            "configurable": configurable,
            "bindable": bindable,
            "configured_profiles_count": configured_profiles_count,
            "configuration_required_reason": ui.get("status_reason") or "",
        }

    def _is_capability_bindable(self, capability, version=None, user_id=None):
        if capability.source in {"archived", "hidden"}:
            return False
        if capability.type != "tool":
            return True
        manifest = (version.manifest if version else {}) or {}
        ui = manifest.get("ui") or {}
        if ui.get("visibility") == "hidden":
            return False
        if ui.get("status") == "requires_config":
            return (
                bool(ui.get("configurable"))
                and self._valid_tool_provider_config_count(user_id, capability.id) > 0
            )
        return bool(ui.get("bindable", ui.get("status") in {"implemented", "partial"}))

    def _valid_tool_provider_config_count(self, user_id, capability_id):
        if not user_id:
            return 0
        from app.models.tool_provider_config import ToolProviderConfig

        return ToolProviderConfig.query.filter_by(
            user_id=user_id,
            capability_id=capability_id,
            status="valid",
        ).count()

    def _version_to_dict(self, version):
        return version.to_dict()

    def _binding_to_dict(self, binding):
        data = binding.to_dict()
        data["capability"] = self._capability_to_dict(binding.capability, include_latest=False)
        data["capability_version"] = self._version_to_dict(binding.capability_version)
        return data

    def _draft_to_dict(self, draft):
        data = draft.to_dict()
        data["source_skill"] = self._capability_to_dict(draft.source_skill, include_latest=False)
        data["source_version"] = self._version_to_dict(draft.source_version)
        return data

    def _call_record_to_dict(self, record):
        data = record.to_dict()
        data["capability"] = self._capability_to_dict(record.capability, include_latest=False)
        data["capability_version"] = self._version_to_dict(record.capability_version)
        return data

    def _capability_bindings_for_user_agents(self, capability_id, user_id):
        return AgentCapabilityBinding.query.join(
            Agent,
            AgentCapabilityBinding.agent_id == Agent.id,
        ).filter(
            AgentCapabilityBinding.capability_id == capability_id,
            Agent.user_id == user_id,
        ).all()

    def _delete_impact(self, capability, user_id):
        bindings = self._capability_bindings_for_user_agents(capability.id, user_id)
        affected = []
        seen = set()
        for binding in bindings:
            if binding.agent_id in seen:
                continue
            seen.add(binding.agent_id)
            affected.append({
                "id": binding.agent.id,
                "name": binding.agent.name,
            })
        return {
            "capability_id": capability.id,
            "name": capability.name,
            "type": capability.type,
            "is_builtin": bool(capability.is_builtin),
            "can_delete": bool(not capability.is_builtin and capability.user_id == user_id),
            "binding_count": len(bindings),
            "call_record_count": CapabilityCallRecord.query.filter_by(
                capability_id=capability.id,
            ).count(),
            "affected_agents": affected,
            "archive_mode": "soft_delete",
        }

    def _latest_plugin_install_record(self, capability):
        record = PluginInstallRecord.query.filter_by(
            plugin_capability_id=capability.id,
        ).order_by(PluginInstallRecord.created_at.desc()).first()
        return record.to_dict() if record else None


capability_service = CapabilityService()
