"""需求管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.requirement_service import requirement_service

requirement_bp = Blueprint('rd_requirements', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@requirement_bp.route('/api/rd/projects/<project_id>/requirements', methods=['GET'])
@jwt_required()
def list_requirements(project_id):
    filters = {}
    for key in ('iteration_id', 'priority', 'status', 'type', 'assignee_id'):
        val = request.args.get(key)
        if val:
            filters[key] = val
    result = requirement_service.list_requirements(project_id, filters)
    return _ok({'items': result, 'total': len(result)})


@requirement_bp.route('/api/rd/projects/<project_id>/requirements', methods=['POST'])
@jwt_required()
def create_requirement(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('title', '').strip():
        return _error('需求标题不能为空')
    result = requirement_service.create_requirement(project_id, data, user_id=_get_user_id())
    return _ok(result, '需求创建成功', 201)


@requirement_bp.route('/api/rd/projects/<project_id>/requirements/<requirement_id>', methods=['GET'])
@jwt_required()
def get_requirement(project_id, requirement_id):
    result = requirement_service.get_requirement(requirement_id)
    if not result:
        return _error('需求不存在', 404)
    return _ok(result)


@requirement_bp.route('/api/rd/projects/<project_id>/requirements/<requirement_id>', methods=['PUT'])
@jwt_required()
def update_requirement(project_id, requirement_id):
    data = request.get_json(silent=True) or {}
    result = requirement_service.update_requirement(requirement_id, data, user_id=_get_user_id())
    if not result:
        return _error('需求不存在', 404)
    return _ok(result, '需求更新成功')


@requirement_bp.route('/api/rd/projects/<project_id>/requirements/<requirement_id>', methods=['DELETE'])
@jwt_required()
def delete_requirement(project_id, requirement_id):
    ok = requirement_service.delete_requirement(requirement_id, user_id=_get_user_id())
    if not ok:
        return _error('需求不存在', 404)
    return _ok({'id': requirement_id}, '需求已删除')


# ── 独立路由（无需 project_id 前缀）──

@requirement_bp.route('/api/rd/requirements/<requirement_id>', methods=['GET'])
@jwt_required()
def get_requirement_standalone(requirement_id):
    result = requirement_service.get_requirement(requirement_id)
    if not result:
        return _error('需求不存在', 404)
    return _ok(result)


@requirement_bp.route('/api/rd/requirements/<requirement_id>', methods=['PUT'])
@jwt_required()
def update_requirement_standalone(requirement_id):
    data = request.get_json(silent=True) or {}
    result = requirement_service.update_requirement(requirement_id, data, user_id=_get_user_id())
    if not result:
        return _error('需求不存在', 404)
    return _ok(result, '需求更新成功')


@requirement_bp.route('/api/rd/requirements/<requirement_id>', methods=['DELETE'])
@jwt_required()
def delete_requirement_standalone(requirement_id):
    ok = requirement_service.delete_requirement(requirement_id, user_id=_get_user_id())
    if not ok:
        return _error('需求不存在', 404)
    return _ok({'id': requirement_id}, '需求已删除')


@requirement_bp.route('/api/rd/requirements/<requirement_id>/status', methods=['PATCH'])
@jwt_required()
def update_requirement_status_standalone(requirement_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if not status:
        return _error('status 不能为空')
    result = requirement_service.update_requirement(requirement_id, {'status': status}, user_id=_get_user_id())
    if not result:
        return _error('需求不存在', 404)
    return _ok(result, '状态已更新')


@requirement_bp.route('/api/rd/requirements/<requirement_id>/move-iteration', methods=['POST'])
@jwt_required()
def move_requirement_iteration_standalone(requirement_id):
    data = request.get_json(silent=True) or {}
    iteration_id = data.get('iteration_id')
    result = requirement_service.update_requirement(requirement_id, {'iteration_id': iteration_id}, user_id=_get_user_id())
    if not result:
        return _error('需求不存在', 404)
    return _ok(result, '需求已移入迭代')


# ── 开发者管理 ──

@requirement_bp.route(
    '/api/rd/projects/<project_id>/requirements/<requirement_id>/assignees',
    methods=['POST']
)
@jwt_required()
def add_assignee(project_id, requirement_id):
    data = request.get_json(silent=True) or {}
    if not data.get('user_id'):
        return _error('user_id 不能为空')
    result = requirement_service.add_assignee(
        requirement_id, data['user_id'],
        role=data.get('role', 'primary'),
        actor_id=_get_user_id()
    )
    if not result:
        return _error('需求不存在', 404)
    return _ok(result, '开发者已添加')


@requirement_bp.route(
    '/api/rd/projects/<project_id>/requirements/<requirement_id>/assignees/<user_id>',
    methods=['DELETE']
)
@jwt_required()
def remove_assignee(project_id, requirement_id, user_id):
    ok = requirement_service.remove_assignee(requirement_id, user_id, actor_id=_get_user_id())
    if not ok:
        return _error('指派关系不存在', 404)
    return _ok({'id': requirement_id}, '开发者已移除')
