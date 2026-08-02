"""活动日志 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from services.activity_service import activity_service

activity_bp = Blueprint('rd_activities', __name__)


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@activity_bp.route('/api/rd/projects/<project_id>/activities', methods=['GET'])
@jwt_required()
def list_activities(project_id):
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    result = activity_service.list_activities(
        project_id, target_type=target_type, target_id=target_id,
        page=page, per_page=per_page
    )
    return _ok(result)
