from app.repositories.base_repo import BaseRepository
from app.models.agent import Agent


class AgentRepository(BaseRepository):
    """Agent repository."""

    def __init__(self):
        super().__init__(Agent)

    def get_public_agents(self):
        """Get all public agents."""
        return Agent.query.filter_by(is_public=True).all()

    def get_user_agents(self, user_id):
        """Get agents created by a user."""
        return Agent.query.filter_by(created_by=user_id).all()

    def get_available_agents(self, user_id=None):
        """Get all agents available to a user (public + user's own)."""
        if user_id:
            return Agent.query.filter(
                (Agent.is_public == True) | (Agent.created_by == user_id)
            ).all()
        return self.get_public_agents()


agent_repo = AgentRepository()
