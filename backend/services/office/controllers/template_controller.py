"""Document template REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.document_service import document_service


template_bp = Blueprint('office_document_templates', __name__)


@template_bp.route('', methods=['GET'])
@jwt_required()
def list_templates():
    result, error = document_service.list_templates(get_jwt_identity(), request.args)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@template_bp.route('', methods=['POST'])
@jwt_required()
def create_template():
    result, error = document_service.create_template(get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Template created', code=201)


@template_bp.route('/<template_id>', methods=['PUT'])
@jwt_required()
def update_template(template_id):
    result, error = document_service.update_template(template_id, get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Template updated')


@template_bp.route('/<template_id>', methods=['DELETE'])
@jwt_required()
def delete_template(template_id):
    result, error = document_service.delete_template(template_id, get_jwt_identity())
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Template deleted')
