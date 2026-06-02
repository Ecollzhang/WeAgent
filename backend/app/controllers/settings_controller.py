from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.settings_service import settings_service
from app.utils.response import success_response, error_response

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/model-config', methods=['GET'])
@jwt_required()
def get_model_config():
    user_id = get_jwt_identity()
    result, error = settings_service.get_model_config(user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result or {
        'api_key': '',
        'has_api_key': False,
        'model': 'claude-3.5-sonnet',
        'custom_model': '',
        'effective_model': 'claude-3.5-sonnet',
        'base_url': '',
        'temperature': 0.7,
        'max_tokens': 4096,
    })


@settings_bp.route('/model-config', methods=['POST'])
@jwt_required()
def save_model_config():
    user_id = get_jwt_identity()
    result, error = settings_service.save_model_config(user_id, request.json or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Model config saved')
