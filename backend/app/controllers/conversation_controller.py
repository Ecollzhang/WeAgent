from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response
from app.schemas.conversation_schema import CreateConversationSchema
from app.services.conversation_service import conversation_service
from marshmallow import ValidationError

conversation_bp = Blueprint('conversations', __name__)


@conversation_bp.route('', methods=['GET'])
@jwt_required()
def list_conversations():
    """Get all conversations for current user, optionally filtered by workspace."""
    user_id = get_jwt_identity()
    workspace_id = request.args.get('workspace_id')
    result, error = conversation_service.get_user_conversations(user_id, workspace_id=workspace_id)

    if error:
        return error_response(error, code=400)

    return success_response(result)


@conversation_bp.route('', methods=['POST'])
@jwt_required()
def create_conversation():
    """Create a new conversation."""
    user_id = get_jwt_identity()

    try:
        schema = CreateConversationSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        print(f'[WeAgent] Create conversation validation failed: {e.messages}; payload={request.get_json(silent=True)}')
        return error_response(str(e.messages), code=400)

    result, error = conversation_service.create_conversation(
        title=data['title'],
        conv_type=data['type'],
        owner_id=user_id,
        participant_ids=data['participant_ids'],
        workspace_id=data.get('workspace_id'),
        kb_domain=data.get('kb_domain') or '',
    )

    if error:
        print(f'[WeAgent] Create conversation failed: {error}; payload={data}')
        return error_response(error, code=400)

    return success_response(result, message='Conversation created', code=201)


@conversation_bp.route('/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get conversation detail."""
    result, error = conversation_service.get_conversation_detail(conversation_id)

    if error:
        return error_response(error, code=404)

    return success_response(result)


@conversation_bp.route('/<conversation_id>/favorite', methods=['POST', 'PATCH'])
@jwt_required()
def update_conversation_favorite(conversation_id):
    """Update conversation favorite state."""
    user_id = get_jwt_identity()
    data = request.json or {}
    result, error = conversation_service.set_conversation_favorite(
        conversation_id,
        user_id,
        data.get('is_favorite', True),
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Conversation updated')


@conversation_bp.route('/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a conversation."""
    user_id = get_jwt_identity()
    result, error = conversation_service.delete_conversation(conversation_id, user_id)

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Conversation deleted')


@conversation_bp.route('/<conversation_id>/participants', methods=['POST'])
@jwt_required()
def add_participant(conversation_id):
    """Add a participant to conversation."""
    user_id = get_jwt_identity()
    data = request.json or {}

    result, error = conversation_service.add_participant(
        conversation_id=conversation_id,
        participant_type=data.get('participant_type', 'user'),
        participant_id=data.get('participant_id'),
        user_id=user_id
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Participant added')


@conversation_bp.route('/<conversation_id>/participants/<participant_type>/<participant_id>', methods=['DELETE'])
@jwt_required()
def remove_participant(conversation_id, participant_type, participant_id):
    """Remove a participant from conversation."""
    user_id = get_jwt_identity()
    result, error = conversation_service.remove_participant(
        conversation_id=conversation_id,
        participant_type=participant_type,
        participant_id=participant_id,
        user_id=user_id
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Participant removed')


@conversation_bp.route('/<conversation_id>/agents/<agent_id>/stop', methods=['POST'])
@jwt_required()
def stop_agent(conversation_id, agent_id):
    """Stop one agent's current execution in a conversation."""
    user_id = get_jwt_identity()
    result, error = conversation_service.stop_agent(conversation_id, agent_id, user_id)

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Agent stopped')


@conversation_bp.route('/<conversation_id>/attachments', methods=['GET'])
@jwt_required()
def list_attachments(conversation_id):
    user_id = get_jwt_identity()
    agent_id = request.args.get('agent_id')
    result, error = conversation_service.list_attachments(conversation_id, user_id, agent_id=agent_id)

    if error:
        return error_response(error, code=400)

    return success_response(result)


@conversation_bp.route('/<conversation_id>/attachments', methods=['POST'])
@jwt_required()
def upload_attachment(conversation_id):
    user_id = get_jwt_identity()
    file = request.files.get('file')
    agent_id = request.form.get('agent_id')
    result, error = conversation_service.upload_attachment(
        conversation_id, user_id, file, agent_id=agent_id
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='File uploaded')


@conversation_bp.route('/<conversation_id>/attachments', methods=['DELETE'])
@jwt_required()
def delete_attachment(conversation_id):
    user_id = get_jwt_identity()
    data = request.json or {}
    result, error = conversation_service.delete_attachment(
        conversation_id, user_id, data.get('path'), data.get('agent_id')
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='File deleted')
