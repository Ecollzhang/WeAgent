"""Meeting and action-item REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.meeting_service import meeting_service


meeting_bp = Blueprint('office_meetings', __name__)


@meeting_bp.route('', methods=['GET'])
@jwt_required()
def list_meetings():
    result, error = meeting_service.list(get_jwt_identity(), request.args)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@meeting_bp.route('', methods=['POST'])
@jwt_required()
def create_meeting():
    result, error = meeting_service.create(get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Meeting created', code=201)


@meeting_bp.route('/<meeting_id>', methods=['GET'])
@jwt_required()
def get_meeting(meeting_id):
    result, error = meeting_service.get(meeting_id, get_jwt_identity())
    if error:
        return error_response(error, code=404)
    return success_response(result)


@meeting_bp.route('/<meeting_id>', methods=['PUT'])
@jwt_required()
def update_meeting(meeting_id):
    result, error = meeting_service.update(
        meeting_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Meeting updated')


@meeting_bp.route('/<meeting_id>', methods=['DELETE'])
@jwt_required()
def delete_meeting(meeting_id):
    result, error = meeting_service.delete(meeting_id, get_jwt_identity())
    if error:
        return error_response(error, code=404)
    return success_response(result, message='Meeting deleted')


@meeting_bp.route('/<meeting_id>/minutes', methods=['POST'])
@jwt_required()
def save_minutes(meeting_id):
    """Save manually edited or AI-generated minutes for a meeting."""
    data = request.get_json(silent=True) or {}
    if 'minutes' not in data:
        return error_response('minutes is required', code=400)
    result, error = meeting_service.update(
        meeting_id, get_jwt_identity(), {'minutes': data['minutes'], 'resolutions': data.get('resolutions', [])}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Meeting minutes saved')


@meeting_bp.route('/<meeting_id>/action-items', methods=['POST'])
@jwt_required()
def create_action_item(meeting_id):
    result, error = meeting_service.create_action_item(
        meeting_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Action item created', code=201)


@meeting_bp.route('/action-items/<action_item_id>', methods=['PUT'])
@jwt_required()
def update_action_item(action_item_id):
    result, error = meeting_service.update_action_item(
        action_item_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Action item updated')
