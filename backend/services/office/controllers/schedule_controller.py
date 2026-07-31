"""Schedule REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.schedule_service import schedule_service


schedule_bp = Blueprint('office_schedules', __name__)


@schedule_bp.route('', methods=['GET'])
@jwt_required()
def list_schedules():
    result, error = schedule_service.list(get_jwt_identity(), request.args)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@schedule_bp.route('', methods=['POST'])
@jwt_required()
def create_schedule():
    result, error = schedule_service.create(get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Schedule created', code=201)


@schedule_bp.route('/<schedule_id>', methods=['PUT'])
@jwt_required()
def update_schedule(schedule_id):
    result, error = schedule_service.update(
        schedule_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Schedule updated')


@schedule_bp.route('/conflicts', methods=['POST'])
@jwt_required()
def check_conflicts():
    result, error = schedule_service.conflicts(get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response({'items': result})
