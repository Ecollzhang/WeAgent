from app import db
from app.models.capability import Capability, CapabilityVersion
from app.models.tool_provider_config import ToolProviderConfig


class ToolProviderConfigService:
    """Manage user provider profiles for configurable Tool capabilities."""

    def list_configs(self, user_id, capability_id):
        capability, _version, _ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        records = ToolProviderConfig.query.filter_by(
            user_id=user_id,
            capability_id=capability.id,
        ).order_by(ToolProviderConfig.created_at.desc()).all()
        return [self._config_to_dict(record) for record in records], None

    def create_config(self, user_id, capability_id, profile_name, provider_type,
                      config=None, secret_refs=None):
        capability, _version, ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        error = self._validate_provider_type(ui, provider_type)
        if error:
            return None, error
        profile_name = (profile_name or "").strip()
        if self._profile_name_exists(user_id, capability.id, profile_name):
            return None, "Provider profile name already exists"
        record = ToolProviderConfig(
            user_id=user_id,
            capability_id=capability.id,
            profile_name=profile_name,
            provider_type=provider_type,
            config=config or {},
            secret_refs=self._normalize_secret_refs(secret_refs),
            status="draft",
        )
        db.session.add(record)
        db.session.commit()
        return self._config_to_dict(record), None

    def update_config(self, user_id, capability_id, config_id, **updates):
        capability, _version, ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        record = self._get_user_config(user_id, capability.id, config_id)
        if not record:
            return None, "Provider config not found"

        profile_name = updates.get("profile_name")
        if profile_name is not None:
            profile_name = profile_name.strip()
            if (
                profile_name != record.profile_name
                and self._profile_name_exists(user_id, capability.id, profile_name)
            ):
                return None, "Provider profile name already exists"
            record.profile_name = profile_name

        provider_type = updates.get("provider_type")
        if provider_type is not None:
            error = self._validate_provider_type(ui, provider_type)
            if error:
                return None, error
            record.provider_type = provider_type

        if updates.get("config") is not None:
            record.config = updates["config"] or {}
        if updates.get("secret_refs") is not None:
            record.secret_refs = self._normalize_secret_refs(updates["secret_refs"])

        record.status = "draft"
        record.last_test_status = ""
        record.last_test_error = ""
        record.last_test_result = {}
        db.session.commit()
        return self._config_to_dict(record), None

    def test_config(self, user_id, capability_id, config_id):
        capability, _version, ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        record = self._get_user_config(user_id, capability.id, config_id)
        if not record:
            return None, "Provider config not found"

        error = self._validate_provider_type(ui, record.provider_type)
        errors = []
        if error:
            errors.append(error)
        errors.extend(self._validate_runtime_config(record.provider_type, record.config or {}))

        if errors:
            record.status = "invalid"
            record.last_test_status = "failed"
            record.last_test_error = "; ".join(errors)
            record.last_test_result = {"checks": errors}
            db.session.commit()
            return self._config_to_dict(record), "Provider config test failed"

        if record.status == "invalid":
            record.status = "draft"
        record.last_test_status = "passed"
        record.last_test_error = ""
        record.last_test_result = {
            "checks": ["provider_type", "runtime_config"],
            "mode": "static",
        }
        db.session.commit()
        return self._config_to_dict(record), None

    def enable_config(self, user_id, capability_id, config_id):
        capability, _version, _ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        record = self._get_user_config(user_id, capability.id, config_id)
        if not record:
            return None, "Provider config not found"
        if record.last_test_status != "passed":
            return None, "Provider config must pass testing before enable"
        record.status = "valid"
        db.session.commit()
        return self._config_to_dict(record), None

    def disable_config(self, user_id, capability_id, config_id):
        capability, _version, _ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        record = self._get_user_config(user_id, capability.id, config_id)
        if not record:
            return None, "Provider config not found"
        record.status = "disabled"
        db.session.commit()
        return self._config_to_dict(record), None

    def delete_config(self, user_id, capability_id, config_id):
        capability, _version, _ui, error = self._get_configurable_tool(
            user_id,
            capability_id,
        )
        if error:
            return None, error
        record = self._get_user_config(user_id, capability.id, config_id)
        if not record:
            return None, "Provider config not found"
        db.session.delete(record)
        db.session.commit()
        return {"deleted": True}, None

    def valid_config_count(self, user_id, capability_id):
        if not user_id:
            return 0
        return ToolProviderConfig.query.filter_by(
            user_id=user_id,
            capability_id=capability_id,
            status="valid",
        ).count()

    def _get_configurable_tool(self, user_id, capability_id):
        capability = Capability.query.filter(
            Capability.id == capability_id,
            ((Capability.is_builtin == True) | (Capability.user_id == user_id)),
            ~Capability.source.in_(["archived", "hidden"]),
        ).first()
        if not capability or capability.type != "tool":
            return None, None, None, "Capability not found"
        version = None
        if capability.latest_version_id:
            version = CapabilityVersion.query.get(capability.latest_version_id)
        ui = ((version.manifest if version else {}) or {}).get("ui") or {}
        if not ui.get("configurable"):
            return None, None, None, "Capability is not configurable"
        return capability, version, ui, None

    def _get_user_config(self, user_id, capability_id, config_id):
        return ToolProviderConfig.query.filter_by(
            id=config_id,
            user_id=user_id,
            capability_id=capability_id,
        ).first()

    def _validate_provider_type(self, ui, provider_type):
        allowed = set(ui.get("provider_types") or [])
        if allowed and provider_type not in allowed:
            return "provider_type is not supported for this capability"
        return None

    def _validate_runtime_config(self, provider_type, config):
        if not isinstance(config, dict):
            return ["config must be an object"]
        if provider_type == "http":
            endpoint = str(config.get("endpoint") or "").strip()
            if not endpoint.startswith(("http://", "https://")):
                return ["endpoint must start with http:// or https://"]
            return []
        if provider_type == "mcp":
            has_runtime = any(
                str(config.get(key) or "").strip()
                for key in ("mcp_runtime_id", "server_command", "command", "package")
            )
            if not has_runtime:
                return ["mcp_runtime_id or command is required"]
            if not str(config.get("tool_name") or "").strip():
                return ["tool_name is required"]
            return []
        if provider_type == "model":
            if not str(config.get("model") or "").strip():
                return ["model is required"]
            return []
        if provider_type == "database":
            errors = []
            if not str(config.get("connection_alias") or "").strip():
                errors.append("connection_alias is required")
            if config.get("readonly") is not True:
                errors.append("readonly must be true")
            driver = config.get("driver")
            if driver and driver not in {"sqlite", "mysql", "postgres"}:
                errors.append("driver must be sqlite, mysql, or postgres")
            return errors
        return ["provider_type is not supported"]

    def _profile_name_exists(self, user_id, capability_id, profile_name):
        return ToolProviderConfig.query.filter_by(
            user_id=user_id,
            capability_id=capability_id,
            profile_name=profile_name,
        ).first() is not None

    def _normalize_secret_refs(self, secret_refs):
        normalized = []
        for ref in secret_refs or []:
            value = str(ref or "").strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    def _config_to_dict(self, record):
        data = record.to_dict()
        data["capability_source_ref"] = record.capability.source_ref if record.capability else ""
        data["capability_name"] = record.capability.name if record.capability else ""
        return data


tool_provider_config_service = ToolProviderConfigService()
