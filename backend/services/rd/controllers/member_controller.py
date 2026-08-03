"""项目成员管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.member_service import member_service

member_bp = Blueprint('rd_members', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@member_bp.route('/api/rd/projects/<project_id>/members', methods=['GET'])
@jwt_required()
def list_members(project_id):
    result = member_service.list_members(project_id)
    return _ok({'items': result, 'total': len(result)})


@member_bp.route('/api/rd/projects/<project_id>/members', methods=['POST'])
@jwt_required()
def add_member(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('user_id'):
        return _error('user_id 不能为空')
    result = member_service.add_member(
        project_id, data['user_id'], role=data.get('role', 'developer')
    )
    return _ok(result, '成员已添加', 201)


@member_bp.route('/api/rd/projects/<project_id>/members/<user_id>', methods=['PUT'])
@jwt_required()
def update_member_role(project_id, user_id):
    data = request.get_json(silent=True) or {}
    if not data.get('role'):
        return _error('role 不能为空')
    result = member_service.update_member_role(project_id, user_id, data['role'])
    if not result:
        return _error('成员不存在', 404)
    return _ok(result, '角色已更新')


@member_bp.route('/api/rd/projects/<project_id>/members/<user_id>', methods=['DELETE'])
@jwt_required()
def remove_member(project_id, user_id):
    ok = member_service.remove_member(project_id, user_id)
    if not ok:
        return _error('成员不存在', 404)
    return _ok({'id': user_id}, '成员已移除')
