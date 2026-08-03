"""迭代管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.iteration_service import iteration_service

iteration_bp = Blueprint('rd_iterations', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@iteration_bp.route('/api/rd/projects/<project_id>/iterations', methods=['GET'])
@jwt_required()
def list_iterations(project_id):
    result = iteration_service.list_iterations(project_id, user_id=_get_user_id())
    return _ok({'items': result, 'total': len(result)})


@iteration_bp.route('/api/rd/projects/<project_id>/iterations', methods=['POST'])
@jwt_required()
def create_iteration(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('name', '').strip():
        return _error('迭代名称不能为空')
    result = iteration_service.create_iteration(project_id, data, user_id=_get_user_id())
    return _ok(result, '迭代创建成功', 201)


@iteration_bp.route('/api/rd/projects/<project_id>/iterations/<iteration_id>', methods=['GET'])
@jwt_required()
def get_iteration(project_id, iteration_id):
    result = iteration_service.get_iteration(iteration_id)
    if not result:
        return _error('迭代不存在', 404)
    return _ok(result)


@iteration_bp.route('/api/rd/projects/<project_id>/iterations/<iteration_id>', methods=['PUT'])
@jwt_required()
def update_iteration(project_id, iteration_id):
    data = request.get_json(silent=True) or {}
    result = iteration_service.update_iteration(iteration_id, data, user_id=_get_user_id())
    if not result:
        return _error('迭代不存在', 404)
    return _ok(result, '迭代更新成功')


@iteration_bp.route('/api/rd/projects/<project_id>/iterations/<iteration_id>', methods=['DELETE'])
@jwt_required()
def delete_iteration(project_id, iteration_id):
    ok = iteration_service.delete_iteration(iteration_id, user_id=_get_user_id())
    if not ok:
        return _error('迭代不存在', 404)
    return _ok({'id': iteration_id}, '迭代已删除')


# ── 独立路由（无需 project_id 前缀）──

@iteration_bp.route('/api/rd/iterations/<iteration_id>', methods=['GET'])
@jwt_required()
def get_iteration_standalone(iteration_id):
    result = iteration_service.get_iteration(iteration_id)
    if not result:
        return _error('迭代不存在', 404)
    return _ok(result)


@iteration_bp.route('/api/rd/iterations/<iteration_id>', methods=['PUT'])
@jwt_required()
def update_iteration_standalone(iteration_id):
    data = request.get_json(silent=True) or {}
    result = iteration_service.update_iteration(iteration_id, data, user_id=_get_user_id())
    if not result:
        return _error('迭代不存在', 404)
    return _ok(result, '迭代更新成功')


@iteration_bp.route('/api/rd/iterations/<iteration_id>', methods=['DELETE'])
@jwt_required()
def delete_iteration_standalone(iteration_id):
    ok = iteration_service.delete_iteration(iteration_id, user_id=_get_user_id())
    if not ok:
        return _error('迭代不存在', 404)
    return _ok({'id': iteration_id}, '迭代已删除')


@iteration_bp.route('/api/rd/iterations/<iteration_id>/status', methods=['PATCH'])
@jwt_required()
def update_iteration_status_standalone(iteration_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if not status:
        return _error('status 不能为空')
    result = iteration_service.update_iteration(iteration_id, {'status': status}, user_id=_get_user_id())
    if not result:
        return _error('迭代不存在', 404)
    return _ok(result, '状态已更新')
