from app.repositories.artifact_repo import artifact_repo


class ArtifactService:
    """Artifact business logic."""

    def create_artifact(self, message_id, artifact_type, title, content='',
                        language='', preview_url='', deploy_url=''):
        """Create a new artifact."""
        artifact = artifact_repo.create(
            message_id=message_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            language=language,
            preview_url=preview_url,
            deploy_url=deploy_url
        )
        return artifact.to_dict(), None

    def get_artifact(self, artifact_id):
        """Get artifact detail."""
        artifact = artifact_repo.get_by_id(artifact_id)
        if not artifact:
            return None, 'Artifact not found'
        return artifact.to_dict(), None

    def get_artifacts_by_message(self, message_id):
        """Get artifacts for a message."""
        artifacts = artifact_repo.get_by_message(message_id)
        return [a.to_dict() for a in artifacts], None

    def update_artifact(self, artifact_id, **kwargs):
        """Update an artifact (create new version)."""
        artifact = artifact_repo.get_by_id(artifact_id)
        if not artifact:
            return None, 'Artifact not found'

        allowed_fields = ['title', 'content', 'language', 'preview_url', 'deploy_url']
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        # Increment version
        current_version = artifact.version
        update_data['version'] = current_version + 1

        artifact = artifact_repo.update(artifact, **update_data)
        return artifact.to_dict(), None


artifact_service = ArtifactService()
