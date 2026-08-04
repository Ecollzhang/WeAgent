"""评论管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.comment_service import comment_service

comment_bp = Blueprint('rd_comments', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@comment_bp.route('/api/rd/projects/<project_id>/comments', methods=['GET'])
@jwt_required()
def list_comments(project_id):
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id')
    result = comment_service.list_comments(project_id, target_type, target_id)
    return _ok({'items': result, 'total': len(result)})


@comment_bp.route('/api/rd/projects/<project_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('content', '').strip():
        return _error('评论内容不能为空')
    if not data.get('target_type') or not data.get('target_id'):
        return _error('target_type 和 target_id 不能为空')
    result = comment_service.create_comment(project_id, data, user_id=_get_user_id())
    return _ok(result, '评论已添加', 201)


@comment_bp.route('/api/rd/projects/<project_id>/comments/<comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(project_id, comment_id):
    data = request.get_json(silent=True) or {}
    result = comment_service.update_comment(comment_id, data, user_id=_get_user_id())
    if not result:
        return _error('评论不存在', 404)
    return _ok(result, '评论已更新')


@comment_bp.route('/api/rd/projects/<project_id>/comments/<comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(project_id, comment_id):
    ok = comment_service.delete_comment(comment_id, user_id=_get_user_id())
    if not ok:
        return _error('评论不存在', 404)
    return _ok({'id': comment_id}, '评论已删除')
