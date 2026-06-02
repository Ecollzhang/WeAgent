from datetime import datetime

from app import db
from app.models.capability import CapabilitySecurityAudit
from app.services.capability_detection_engine import audit_files
from app.services.capability_import_security import validate_bundle_files


class CapabilitySecurityAuditService:
    """Persist security audits and enforce expert override for high risk."""

    def audit_and_record(self, user_id, files, capability_id=None,
                         capability_version_id=None, import_job_id=None,
                         draft_id=None, override_confirmed=False,
                         override_reason=""):
        security_report = validate_bundle_files(files or [])
        detection_report = audit_files(files or [])
        report = self._merge_reports(security_report, detection_report)

        if report["risk_level"] == "high" and not override_confirmed:
            return None, "High-risk audit requires expert override"
        if report["risk_level"] == "high" and not str(override_reason or "").strip():
            return None, "High-risk audit override requires a reason"

        record = CapabilitySecurityAudit(
            user_id=user_id,
            capability_id=capability_id,
            capability_version_id=capability_version_id,
            import_job_id=import_job_id,
            draft_id=draft_id,
            risk_level=report["risk_level"],
            risk_items=report["risk_items"],
            blocking_items=report["blocking_items"],
            inferred_permissions=report["inferred_permissions"],
            overridden=bool(override_confirmed and report["risk_level"] == "high"),
            override_reason=override_reason or "",
            confirmed_at=datetime.utcnow() if override_confirmed else None,
        )
        db.session.add(record)
        db.session.commit()
        return record.to_dict(), None

    def latest_for_capability(self, capability_id):
        record = CapabilitySecurityAudit.query.filter_by(
            capability_id=capability_id,
        ).order_by(CapabilitySecurityAudit.created_at.desc()).first()
        return record.to_dict() if record else None

    def _merge_reports(self, *reports):
        risk_items = []
        blocking_items = []
        permissions = set()
        scanned_files = set()
        for report in reports:
            risk_items.extend(report.get("risk_items") or [])
            blocking_items.extend(report.get("blocking_items") or [])
            permissions.update(report.get("inferred_permissions") or [])
            scanned_files.update(report.get("scanned_files") or [])
        return {
            "risk_level": self._risk_level(risk_items),
            "risk_items": risk_items,
            "blocking_items": blocking_items,
            "inferred_permissions": sorted(permissions),
            "scanned_files": sorted(scanned_files),
        }

    def _risk_level(self, risk_items):
        severities = {item.get("severity") for item in risk_items}
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"


capability_security_audit_service = CapabilitySecurityAuditService()
