from app.models.capability import (
    AgentCapabilityBinding,
    Capability,
    CapabilityCallRecord,
    CapabilityVersion,
    SkillRevisionDraft,
)
from app.repositories.base_repo import BaseRepository


class CapabilityRepository(BaseRepository):
    def __init__(self):
        super().__init__(Capability)

    def visible_to_user(self, user_id, capability_type=None):
        query = Capability.query.filter(
            (Capability.is_builtin == True) | (Capability.user_id == user_id)
        )
        if capability_type:
            query = query.filter(Capability.type == capability_type)
        return query.order_by(Capability.created_at.desc()).all()

    def get_version(self, version_id):
        return CapabilityVersion.query.get(version_id)

    def get_agent_binding(self, agent_id, capability_id):
        return AgentCapabilityBinding.query.filter_by(
            agent_id=agent_id,
            capability_id=capability_id,
        ).first()

    def get_agent_bindings(self, agent_id):
        return AgentCapabilityBinding.query.filter_by(agent_id=agent_id).all()


capability_repo = CapabilityRepository()
capability_version_repo = BaseRepository(CapabilityVersion)
agent_capability_binding_repo = BaseRepository(AgentCapabilityBinding)
capability_call_record_repo = BaseRepository(CapabilityCallRecord)
skill_revision_draft_repo = BaseRepository(SkillRevisionDraft)
