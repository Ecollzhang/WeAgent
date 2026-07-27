from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message
from app.repositories.artifact_repo import artifact_repo


class ArtifactService:
    """Artifact business logic with object-level access control."""

    @staticmethod
    def _message_for_user(message_id, user_id):
        if not message_id:
            return None
        message = Message.query.filter_by(id=message_id).first()
        if not message:
            return None
        conversation = Conversation.query.filter_by(id=message.conversation_id).first()
        if not conversation:
            return None
        if conversation.owner_id == user_id:
            return message
        participant = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id,
            participant_type="user",
            participant_id=user_id,
        ).first()
        return message if participant else None

    def _artifact_for_user(self, artifact_id, user_id):
        artifact = artifact_repo.get_by_id(artifact_id)
        if not artifact:
            return None
        if artifact.owner_user_id == user_id:
            return artifact
        if artifact.message_id and self._message_for_user(artifact.message_id, user_id):
            return artifact
        return None

    def create_artifact(self, user_id, message_id, artifact_type, title, content='',
                        language='', preview_url='', deploy_url=''):
        if message_id and not self._message_for_user(message_id, user_id):
            return None, 'Message not found'
        artifact = artifact_repo.create(
            owner_user_id=user_id,
            message_id=message_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            language=language,
            preview_url=preview_url,
            deploy_url=deploy_url
        )
        return artifact.to_dict(), None

    def get_artifact(self, artifact_id, user_id):
        artifact = self._artifact_for_user(artifact_id, user_id)
        if not artifact:
            return None, 'Artifact not found'
        return artifact.to_dict(), None

    def get_artifacts_by_message(self, message_id, user_id):
        if not self._message_for_user(message_id, user_id):
            return None, 'Message not found'
        artifacts = artifact_repo.get_by_message(message_id)
        return [artifact.to_dict() for artifact in artifacts], None

    def update_artifact(self, artifact_id, user_id, **kwargs):
        artifact = self._artifact_for_user(artifact_id, user_id)
        if not artifact:
            return None, 'Artifact not found'

        allowed_fields = ['title', 'content', 'language', 'preview_url', 'deploy_url']
        update_data = {
            key: value for key, value in kwargs.items()
            if key in allowed_fields and value is not None
        }
        update_data['version'] = artifact.version + 1
        artifact = artifact_repo.update(artifact, **update_data)
        return artifact.to_dict(), None


artifact_service = ArtifactService()
