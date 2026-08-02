"""Bug 管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.bug_service import bug_service

bug_bp = Blueprint('rd_bugs', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@bug_bp.route('/api/rd/projects/<project_id>/bugs', methods=['GET'])
@jwt_required()
def list_bugs(project_id):
    filters = {}
    for key in ('iteration_id', 'severity', 'priority', 'status', 'assignee_id'):
        val = request.args.get(key)
        if val:
            filters[key] = val
    result = bug_service.list_bugs(project_id, filters)
    return _ok({'items': result, 'total': len(result)})


@bug_bp.route('/api/rd/projects/<project_id>/bugs', methods=['POST'])
@jwt_required()
def create_bug(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('title', '').strip():
        return _error('Bug 标题不能为空')
    result = bug_service.create_bug(project_id, data, user_id=_get_user_id())
    return _ok(result, 'Bug 创建成功', 201)


@bug_bp.route('/api/rd/projects/<project_id>/bugs/<bug_id>', methods=['GET'])
@jwt_required()
def get_bug(project_id, bug_id):
    result = bug_service.get_bug(bug_id)
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result)


@bug_bp.route('/api/rd/projects/<project_id>/bugs/<bug_id>', methods=['PUT'])
@jwt_required()
def update_bug(project_id, bug_id):
    data = request.get_json(silent=True) or {}
    result = bug_service.update_bug(bug_id, data, user_id=_get_user_id())
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result, 'Bug 更新成功')


@bug_bp.route('/api/rd/projects/<project_id>/bugs/<bug_id>', methods=['DELETE'])
@jwt_required()
def delete_bug(project_id, bug_id):
    ok = bug_service.delete_bug(bug_id, user_id=_get_user_id())
    if not ok:
        return _error('Bug 不存在', 404)
    return _ok({'id': bug_id}, 'Bug 已删除')


# ── 修复人管理 ──

@bug_bp.route(
    '/api/rd/projects/<project_id>/bugs/<bug_id>/assignees',
    methods=['POST']
)
@jwt_required()
def add_assignee(project_id, bug_id):
    data = request.get_json(silent=True) or {}
    if not data.get('user_id'):
        return _error('user_id 不能为空')
    result = bug_service.add_assignee(
        bug_id, data['user_id'],
        role=data.get('role', 'fixer'),
        actor_id=_get_user_id()
    )
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result, '修复人已添加')


@bug_bp.route(
    '/api/rd/projects/<project_id>/bugs/<bug_id>/assignees/<user_id>',
    methods=['DELETE']
)
@jwt_required()
def remove_assignee(project_id, bug_id, user_id):
    ok = bug_service.remove_assignee(bug_id, user_id, actor_id=_get_user_id())
    if not ok:
        return _error('指派关系不存在', 404)
    return _ok({'id': bug_id}, '修复人已移除')


# ── 独立路由（无需 project_id 前缀）──

@bug_bp.route('/api/rd/bugs/<bug_id>', methods=['GET'])
@jwt_required()
def get_bug_standalone(bug_id):
    result = bug_service.get_bug(bug_id)
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result)


@bug_bp.route('/api/rd/bugs/<bug_id>', methods=['PUT'])
@jwt_required()
def update_bug_standalone(bug_id):
    data = request.get_json(silent=True) or {}
    result = bug_service.update_bug(bug_id, data, user_id=_get_user_id())
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result, 'Bug 更新成功')


@bug_bp.route('/api/rd/bugs/<bug_id>', methods=['DELETE'])
@jwt_required()
def delete_bug_standalone(bug_id):
    ok = bug_service.delete_bug(bug_id, user_id=_get_user_id())
    if not ok:
        return _error('Bug 不存在', 404)
    return _ok({'id': bug_id}, 'Bug 已删除')


@bug_bp.route('/api/rd/bugs/<bug_id>/status', methods=['PATCH'])
@jwt_required()
def update_bug_status_standalone(bug_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if not status:
        return _error('status 不能为空')
    result = bug_service.update_bug(bug_id, {'status': status}, user_id=_get_user_id())
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result, '状态已更新')


@bug_bp.route('/api/rd/bugs/<bug_id>/move-iteration', methods=['POST'])
@jwt_required()
def move_bug_iteration_standalone(bug_id):
    data = request.get_json(silent=True) or {}
    iteration_id = data.get('iteration_id')
    result = bug_service.update_bug(bug_id, {'iteration_id': iteration_id}, user_id=_get_user_id())
    if not result:
        return _error('Bug 不存在', 404)
    return _ok(result, 'Bug 已移入迭代')
