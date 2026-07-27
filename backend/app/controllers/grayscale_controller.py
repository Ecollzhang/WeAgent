"""Grayscale REST API — 灰度配置管理（仅管理员可操作）."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils.response import success_response, error_response
from app.utils.admin_required import admin_required
from app.services.grayscale_service import grayscale_service

grayscale_bp = Blueprint('grayscale', __name__)


# ------------------------------------------------------------------
# 公共接口 — 前端按领域拉取灰度配置
# ------------------------------------------------------------------

@grayscale_bp.route('/api/grayscale/config', methods=['GET'])
@jwt_required()
def get_grayscale_by_domain():
    """获取指定领域的全部灰度配置（公开接口，所有登录用户可用）."""
    domain = request.args.get('domain')
    if not domain:
        return error_response('Domain parameter is required', code=400)
    if domain not in ('common', 'rd', 'edu', 'office'):
        return error_response("Invalid domain. Must be one of: common, rd, edu, office", code=400)
    result, error = grayscale_service.get_by_domain(domain)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@grayscale_bp.route('/api/grayscale/domains', methods=['GET'])
@jwt_required()
def get_grayscale_domains():
    """获取所有有灰度配置的领域列表."""
    result, error = grayscale_service.get_domains()
    if error:
        return error_response(error, code=400)
    return success_response(result)


# ------------------------------------------------------------------
# 管理接口 — 仅 admin 角色可操作
# ------------------------------------------------------------------

@grayscale_bp.route('/api/admin/grayscale/<int:config_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_grayscale(config_id):
    """更新单条灰度配置."""
    data = request.get_json(silent=True) or {}
    result, error = grayscale_service.update(config_id, data)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Grayscale config updated')


@grayscale_bp.route('/api/admin/grayscale/batch', methods=['POST'])
@jwt_required()
@admin_required()
def batch_update_grayscale():
    """批量更新灰度配置."""
    data = request.get_json(silent=True) or {}
    updates = data.get('updates', [])
    if not updates:
        return error_response('No updates provided', code=400)
    result, error = grayscale_service.batch_update(updates)
    if error:
        return error_response(error, code=400)
    return success_response(result, message=f'{result["updated"]} configs updated')


@grayscale_bp.route('/api/admin/grayscale', methods=['POST'])
@jwt_required()
@admin_required()
def create_grayscale():
    """新建灰度配置."""
    data = request.get_json(silent=True) or {}
    result, error = grayscale_service.create(data)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Grayscale config created', code=201)


@grayscale_bp.route('/api/admin/grayscale/<int:config_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_grayscale(config_id):
    """删除灰度配置."""
    result, error = grayscale_service.delete(config_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Grayscale config deleted')
