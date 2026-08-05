from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.utils.response import success_response, error_response
from app.schemas.artifact_schema import CreateArtifactSchema
from app.services.artifact_service import artifact_service
from marshmallow import ValidationError

artifact_bp = Blueprint('artifacts', __name__)


@artifact_bp.route('', methods=['POST'])
@jwt_required()
def create_artifact():
    """Create a new artifact."""
    try:
        schema = CreateArtifactSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = artifact_service.create_artifact(
        user_id=get_jwt_identity(),
        message_id=data.get('message_id'),
        artifact_type=data['artifact_type'],
        title=data['title'],
        content=data.get('content', ''),
        language=data.get('language', ''),
        preview_url=data.get('preview_url', ''),
        deploy_url=data.get('deploy_url', '')
    )

    if error:
        return error_response(error, code=404)

    return success_response(result, message='Artifact created', code=201)


@artifact_bp.route('/<artifact_id>', methods=['GET'])
@jwt_required()
def get_artifact(artifact_id):
    """Get artifact detail."""
    result, error = artifact_service.get_artifact(artifact_id, get_jwt_identity())

    if error:
        return error_response(error, code=404)

    return success_response(result)


@artifact_bp.route('/message/<message_id>', methods=['GET'])
@jwt_required()
def get_artifacts_by_message(message_id):
    """Get artifacts for a message."""
    result, error = artifact_service.get_artifacts_by_message(
        message_id, get_jwt_identity()
    )

    if error:
        return error_response(error, code=404)

    return success_response(result)


@artifact_bp.route('/<artifact_id>', methods=['PUT'])
@jwt_required()
def update_artifact(artifact_id):
    """Update an artifact."""
    data = request.json or {}

    result, error = artifact_service.update_artifact(
        artifact_id, get_jwt_identity(), **data
    )

    if error:
        return error_response(error, code=404)

    return success_response(result, message='Artifact updated')
