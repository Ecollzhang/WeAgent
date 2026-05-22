from app.repositories.base_repo import BaseRepository
from app.models.artifact import Artifact


class ArtifactRepository(BaseRepository):
    """Artifact repository."""

    def __init__(self):
        super().__init__(Artifact)

    def get_by_message(self, message_id):
        """Get artifacts for a specific message."""
        return Artifact.query.filter_by(message_id=message_id).all()


artifact_repo = ArtifactRepository()
