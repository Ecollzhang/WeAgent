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
    """Get all conversations for current user."""
    user_id = get_jwt_identity()
    result, error = conversation_service.get_user_conversations(user_id)

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
        return error_response(str(e.messages), code=400)

    result, error = conversation_service.create_conversation(
        title=data['title'],
        conv_type=data['type'],
        owner_id=user_id,
        participant_ids=data['participant_ids']
    )

    if error:
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
