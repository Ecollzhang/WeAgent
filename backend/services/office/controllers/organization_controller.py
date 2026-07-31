from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.utils.response import success_response, error_response
from services.organization_service import organization_service

organization_bp = Blueprint('office_organization', __name__)

def _result(result, error, code=400):
    return error_response(error, code=code) if error else success_response(result)

@organization_bp.route('', methods=['GET'])
@jwt_required()
def get_organization():
    return _result(*organization_service.get_structure(request.args.get('workspace_id', '').strip(), get_jwt_identity()))

@organization_bp.route('/bootstrap', methods=['POST'])
@jwt_required()
def bootstrap():
    data=request.get_json(silent=True) or {}
    return _result(*organization_service.bootstrap((data.get('workspace_id') or '').strip(), get_jwt_identity(), data), code=400)

@organization_bp.route('/groups', methods=['POST'])
@jwt_required()
def create_group():
    data=request.get_json(silent=True) or {}
    return _result(*organization_service.create_group((data.get('workspace_id') or '').strip(), get_jwt_identity(), data))

@organization_bp.route('/members', methods=['POST'])
@jwt_required()
def add_member():
    data=request.get_json(silent=True) or {}
    return _result(*organization_service.add_member((data.get('workspace_id') or '').strip(), get_jwt_identity(), data))

@organization_bp.route('/members/<member_id>', methods=['PUT'])
@jwt_required()
def update_member(member_id):
    data=request.get_json(silent=True) or {}
    return _result(*organization_service.update_member((data.get('workspace_id') or '').strip(), get_jwt_identity(), member_id, data))

@organization_bp.route('/notifications', methods=['GET'])
@jwt_required()
def notifications():
    return _result(*organization_service.notifications(request.args.get('workspace_id', '').strip(), get_jwt_identity()))

@organization_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@jwt_required()
def read_notification(notification_id):
    return _result(*organization_service.read_notification(notification_id, get_jwt_identity()))
