"""Workspace REST API — 工作空间 CRUD."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response
from app.services.workspace_service import workspace_service

workspace_bp = Blueprint('workspace', __name__)


@workspace_bp.route('/api/workspaces', methods=['POST'])
@jwt_required()
def create_workspace():
    """创建工作空间."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    result, error = workspace_service.create(user_id, data)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Workspace created', code=201)


@workspace_bp.route('/api/workspaces', methods=['GET'])
@jwt_required()
def list_workspaces():
    """获取当前用户的工作空间列表."""
    user_id = get_jwt_identity()
    domain = request.args.get('domain')
    result, error = workspace_service.list_by_user(user_id, domain=domain)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@workspace_bp.route('/api/workspaces/<workspace_id>', methods=['GET'])
@jwt_required()
def get_workspace(workspace_id):
    """获取单个工作空间详情."""
    user_id = get_jwt_identity()
    result, error = workspace_service.get_by_id(workspace_id, user_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@workspace_bp.route('/api/workspaces/<workspace_id>', methods=['PUT'])
@jwt_required()
def update_workspace(workspace_id):
    """更新工作空间."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    result, error = workspace_service.update(workspace_id, user_id, data)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Workspace updated')


@workspace_bp.route('/api/workspaces/<workspace_id>', methods=['DELETE'])
@jwt_required()
def archive_workspace(workspace_id):
    """归档工作空间."""
    user_id = get_jwt_identity()
    result, error = workspace_service.archive(workspace_id, user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Workspace archived')
