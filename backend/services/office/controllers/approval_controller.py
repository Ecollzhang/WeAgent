"""Approval REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.approval_service import approval_service


approval_bp = Blueprint('office_approvals', __name__)


@approval_bp.route('', methods=['GET'])
@jwt_required()
def list_approvals():
    result, error = approval_service.list(get_jwt_identity(), request.args)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@approval_bp.route('/<approval_id>', methods=['GET'])
@jwt_required()
def get_approval(approval_id):
    result, error = approval_service.get(approval_id, get_jwt_identity())
    if error:
        return error_response(error, code=404 if error == 'Approval not found' else 403)
    return success_response(result)


@approval_bp.route('/<approval_id>/approve', methods=['POST'])
@jwt_required()
def approve(approval_id):
    data = request.get_json(silent=True) or {}
    result, error = approval_service.approve(approval_id, get_jwt_identity(), data.get('comment', ''))
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Approval approved')


@approval_bp.route('/<approval_id>/reject', methods=['POST'])
@jwt_required()
def reject(approval_id):
    data = request.get_json(silent=True) or {}
    result, error = approval_service.reject(approval_id, get_jwt_identity(), data.get('comment', ''))
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Approval rejected')


@approval_bp.route('/<approval_id>/withdraw', methods=['POST'])
@jwt_required()
def withdraw(approval_id):
    result, error = approval_service.withdraw(approval_id, get_jwt_identity())
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Approval withdrawn')
