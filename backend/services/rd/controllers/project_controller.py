"""项目管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.project_service import project_service

project_bp = Blueprint('rd_projects', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


# ── 项目 CRUD ─────────────────────────────────────────

@project_bp.route('/api/rd/projects', methods=['GET'])
@jwt_required()
def list_projects():
    """获取用户的项目列表."""
    user_id = _get_user_id()
    workspace_id = request.args.get('workspace_id')
    result = project_service.list_projects(user_id, workspace_id=workspace_id)
    return _ok({'items': result, 'total': len(result)})


@project_bp.route('/api/rd/projects', methods=['POST'])
@jwt_required()
def create_project():
    """创建新项目."""
    user_id = _get_user_id()
    data = request.get_json(silent=True) or {}
    if not data.get('name', '').strip():
        return _error('项目名称不能为空')
    if len(data.get('name', '').strip()) > 200:
        return _error('项目名称不能超过200个字符')

    result = project_service.create_project(user_id, data)
    return _ok(result, '项目创建成功', 201)


@project_bp.route('/api/rd/projects/<project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """获取项目详情（含文件列表）."""
    result = project_service.get_project(project_id, user_id=_get_user_id())
    if not result:
        return _error('项目不存在', 404)
    return _ok(result)


@project_bp.route('/api/rd/projects/<project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """更新项目信息."""
    data = request.get_json(silent=True) or {}
    result = project_service.update_project(project_id, _get_user_id(), data)
    if not result:
        return _error('项目不存在', 404)
    return _ok(result, '项目更新成功')


@project_bp.route('/api/rd/projects/<project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """归档项目."""
    ok = project_service.delete_project(project_id, _get_user_id())
    if not ok:
        return _error('项目不存在', 404)
    return _ok({'id': project_id}, '项目已归档')


# ── 项目文件管理 ─────────────────────────────────────

@project_bp.route('/api/rd/projects/<project_id>/files', methods=['GET'])
@jwt_required()
def list_files(project_id):
    """获取项目文件列表."""
    result = project_service.list_files(project_id, user_id=_get_user_id())
    if result is None:
        return _error('项目不存在', 404)
    return _ok({'items': result, 'total': len(result)})


@project_bp.route('/api/rd/projects/<project_id>/files/<file_id>', methods=['GET'])
@jwt_required()
def get_file(project_id, file_id):
    """获取文件内容."""
    result = project_service.get_file(file_id, user_id=_get_user_id())
    if not result:
        return _error('文件不存在', 404)
    return _ok(result)


@project_bp.route('/api/rd/projects/<project_id>/files', methods=['POST'])
@jwt_required()
def add_file(project_id):
    """向项目添加文件."""
    data = request.get_json(silent=True) or {}
    if not data.get('file_name'):
        return _error('file_name 不能为空')
    result = project_service.add_file(project_id, _get_user_id(), data)
    if result is None:
        return _error('项目不存在', 404)
    return _ok(result, '文件已添加', 201)


@project_bp.route('/api/rd/projects/<project_id>/files/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(project_id, file_id):
    """删除文件."""
    ok = project_service.delete_file(file_id, _get_user_id())
    if not ok:
        return _error('文件不存在', 404)
    return _ok({'id': file_id}, '文件已删除')


# ── 项目上下文（供 Agent 感知对话）────────────────────

@project_bp.route('/api/rd/projects/<project_id>/context', methods=['GET'])
@jwt_required()
def get_project_context(project_id):
    """获取项目上下文 — 用于 Agent 系统提示词注入."""
    result = project_service.get_project_context(project_id, user_id=_get_user_id())
    if not result:
        return _error('项目不存在', 404)
    return _ok(result)


@project_bp.route('/api/rd/projects/<project_id>/gantt', methods=['GET'])
@jwt_required()
def get_gantt_data(project_id):
    """获取甘特图数据."""
    result = project_service.get_gantt_data(project_id, user_id=_get_user_id())
    if not result:
        return _error('项目不存在', 404)
    return _ok(result)
