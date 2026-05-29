from app import db
from app.models.agent import Agent
from app.models.capability import Capability, CapabilityVersion, SkillRevisionDraft


class CapabilityDraftSyncService:
    """Persist sandbox-side runtime Skill edits as pending user drafts."""

    def sync_records(self, user_id, records):
        if not isinstance(records, list):
            return None, "Records must be a list"

        synced = []
        for record in records:
            error = self._validate_record(record)
            if error:
                return None, error

            agent = Agent.query.filter_by(id=record["agent_id"], user_id=user_id).first()
            if not agent:
                return None, "Agent not found"

            skill = Capability.query.filter(
                Capability.id == record["source_skill_id"],
                Capability.type == "skill",
                (Capability.is_builtin == True) | (Capability.user_id == user_id),  # noqa: E712
            ).first()
            if not skill:
                return None, "Skill capability not found"

            version = CapabilityVersion.query.filter_by(
                id=record["source_version_id"],
                capability_id=skill.id,
            ).first()
            if not version:
                return None, "Skill version not found"

            existing = self._find_existing_pending_draft(record)
            if existing:
                synced.append(existing)
                continue

            draft = SkillRevisionDraft(
                source_skill_id=skill.id,
                source_version_id=version.id,
                session_id=record["session_id"],
                agent_id=agent.id,
                diff=record.get("diff") or {},
                full_markdown=record.get("full_markdown") or "",
                status="pending_review",
            )
            db.session.add(draft)
            db.session.flush()
            synced.append(draft)

        db.session.commit()
        return [self._draft_to_dict(draft) for draft in synced], None

    def _validate_record(self, record):
        if not isinstance(record, dict):
            return "Draft record must be an object"
        required = [
            "session_id",
            "agent_id",
            "source_skill_id",
            "source_version_id",
            "full_markdown",
        ]
        missing = [field for field in required if not record.get(field)]
        if missing:
            return f"Draft record missing fields: {', '.join(missing)}"
        return None

    def _find_existing_pending_draft(self, record):
        new_checksum = (record.get("diff") or {}).get("new_checksum")
        candidates = SkillRevisionDraft.query.filter_by(
            source_skill_id=record["source_skill_id"],
            source_version_id=record["source_version_id"],
            session_id=record["session_id"],
            agent_id=record["agent_id"],
            status="pending_review",
        ).all()
        if not new_checksum:
            return None
        for candidate in candidates:
            if (candidate.diff or {}).get("new_checksum") == new_checksum:
                return candidate
        return None

    def _draft_to_dict(self, draft):
        data = draft.to_dict()
        data["source_skill"] = draft.source_skill.to_dict() if draft.source_skill else None
        data["source_version"] = draft.source_version.to_dict() if draft.source_version else None
        return data


capability_draft_sync_service = CapabilityDraftSyncService()
