from app import db
from app.models.capability import (
    Capability,
    CapabilityImportJob,
    CapabilitySecurityAudit,
    CapabilityVersion,
    CapabilityVersionAsset,
)
from app.services.capability_security_audit_service import (
    capability_security_audit_service,
)
from app.services.capability_service import capability_service


class CapabilityImportConfirmService:
    """Persist selected preview candidates as capabilities."""

    def confirm_import_job(self, user_id, import_job_id, selected_entries=None,
                           category_id=None, category_slug=None,
                           override_confirmed=False, override_reason=""):
        job = CapabilityImportJob.query.filter_by(
            id=import_job_id,
            user_id=user_id,
        ).first()
        if not job:
            return None, "Import job not found"
        if job.status != "previewed":
            return None, "Import job is not previewable"

        payload = job.preview_payload or {}
        audit = payload.get("audit") or {}
        if audit.get("risk_level") == "high" and not override_confirmed:
            return None, "High-risk import requires expert override"
        if audit.get("risk_level") == "high" and not str(override_reason or "").strip():
            return None, "High-risk import override requires a reason"

        bundle_files = payload.get("bundle_files") or []
        selected = set(selected_entries or [])
        created = []
        for candidate in payload.get("capabilities") or []:
            entry = candidate.get("entry")
            if selected and entry not in selected:
                continue
            candidate_files = self._files_for_candidate(bundle_files, candidate)
            if candidate.get("manifest"):
                result, error = self._confirm_manifest_candidate(
                    user_id=user_id,
                    job=job,
                    candidate=candidate,
                    category_id=category_id,
                    category_slug=category_slug,
                )
                if error:
                    return None, error
                for item in result:
                    audit_record, audit_error = capability_security_audit_service.audit_and_record(
                        user_id=user_id,
                        files=candidate_files,
                        capability_id=item["id"],
                        capability_version_id=item["latest_version"]["id"],
                        import_job_id=job.id,
                        override_confirmed=override_confirmed,
                        override_reason=override_reason,
                    )
                    if audit_error:
                        return None, audit_error
                    item["latest_audit"] = audit_record
                    created.append(item)
                continue
            skill_file = self._find_file(bundle_files, entry)
            if not skill_file:
                return None, f"Selected Skill file not found: {entry}"
            permissions = {
                "required": [],
                "optional": audit.get("inferred_permissions") or [],
            }
            result, error = capability_service.create_skill(
                user_id=user_id,
                name=candidate.get("name") or "Imported Skill",
                markdown=skill_file.get("content") or "",
                description=candidate.get("description") or "",
                permissions=permissions,
                meta={
                    "import_job_id": job.id,
                    "entry": entry,
                    "source_type": job.source_type,
                },
                source=job.source_type,
                source_ref=job.source_ref,
                category_id=category_id,
                category_slug=category_slug,
                assets=candidate_files,
            )
            if error:
                return None, error
            audit_record, audit_error = capability_security_audit_service.audit_and_record(
                user_id=user_id,
                files=candidate_files,
                capability_id=result["id"],
                capability_version_id=result["latest_version"]["id"],
                import_job_id=job.id,
                override_confirmed=override_confirmed,
                override_reason=override_reason,
            )
            if audit_error:
                return None, audit_error
            result["latest_audit"] = audit_record
            created.append(result)

        job.status = "confirmed"
        db.session.commit()
        return created, None

    def _confirm_manifest_candidate(self, user_id, job, candidate,
                                    category_id=None, category_slug=None):
        manifest = candidate.get("manifest") or {}
        capabilities = manifest.get("capabilities") or []
        index = candidate.get("manifest_index")
        if index is None or index >= len(capabilities):
            return None, f"Selected manifest capability not found: {candidate.get('entry')}"
        filtered_manifest = {
            **manifest,
            "capabilities": [capabilities[index]],
        }
        return capability_service.import_npx_manifest(
            user_id=user_id,
            manifest=filtered_manifest,
            source_ref=job.source_ref,
            category_id=category_id,
            category_slug=category_slug,
        )

    def list_assets(self, user_id, capability_id, version_id=None):
        version, error = self._visible_version(user_id, capability_id, version_id)
        if error:
            return None, error
        assets = CapabilityVersionAsset.query.filter_by(
            capability_version_id=version.id,
        ).order_by(CapabilityVersionAsset.path.asc()).all()
        return [asset.to_dict() for asset in assets], None

    def list_audits(self, user_id, capability_id):
        capability = self._visible_capability(user_id, capability_id)
        if not capability:
            return None, "Capability not found"
        audits = CapabilitySecurityAudit.query.filter_by(
            capability_id=capability.id,
        ).order_by(CapabilitySecurityAudit.created_at.desc()).all()
        return [audit.to_dict() for audit in audits], None

    def _visible_version(self, user_id, capability_id, version_id=None):
        capability = self._visible_capability(user_id, capability_id)
        if not capability:
            return None, "Capability not found"
        resolved_version_id = version_id or capability.latest_version_id
        version = CapabilityVersion.query.filter_by(
            id=resolved_version_id,
            capability_id=capability.id,
        ).first()
        if not version:
            return None, "Capability version not found"
        return version, None

    def _visible_capability(self, user_id, capability_id):
        return Capability.query.filter(
            Capability.id == capability_id,
            (Capability.is_builtin == True) | (Capability.user_id == user_id),  # noqa: E712
        ).first()

    def _find_file(self, files, path):
        for item in files:
            if item.get("path") == path:
                return item
        return None

    def _files_for_candidate(self, files, candidate):
        manifest_path = candidate.get("manifest_path")
        if manifest_path:
            return [
                item for item in files
                if item.get("path") == manifest_path
            ]
        root = candidate.get("root") or ""
        entry = candidate.get("entry")
        if not root:
            return [
                item for item in files
                if item.get("path") == entry or "/" not in item.get("path", "")
            ]
        return [
            item for item in files
            if item.get("path") == entry or item.get("path", "").startswith(f"{root}/")
        ]


capability_import_confirm_service = CapabilityImportConfirmService()
