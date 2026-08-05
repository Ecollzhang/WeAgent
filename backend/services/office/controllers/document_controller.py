"""Official document REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.document_service import document_service


document_bp = Blueprint('office_documents', __name__)


@document_bp.route('', methods=['GET'])
@jwt_required()
def list_documents():
    result, error = document_service.list_documents(get_jwt_identity(), request.args)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@document_bp.route('', methods=['POST'])
@jwt_required()
def create_document():
    result, error = document_service.create_document(get_jwt_identity(), request.get_json(silent=True) or {})
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Document created', code=201)


@document_bp.route('/<document_id>', methods=['GET'])
@jwt_required()
def get_document(document_id):
    result, error = document_service.get_document(document_id, get_jwt_identity())
    if error:
        return error_response(error, code=404)
    return success_response(result)


@document_bp.route('/<document_id>', methods=['PUT'])
@jwt_required()
def update_document(document_id):
    result, error = document_service.update_document(
        document_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Document updated')


@document_bp.route('/from-meeting/<meeting_id>', methods=['POST'])
@jwt_required()
def create_from_meeting(meeting_id):
    result, error = document_service.create_from_meeting(
        meeting_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Document draft created', code=201)


@document_bp.route('/<document_id>/submit', methods=['POST'])
@jwt_required()
def submit_document(document_id):
    result, error = document_service.submit(
        document_id, get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Document submitted')


@document_bp.route('/<document_id>/publish', methods=['POST'])
@jwt_required()
def publish_document(document_id):
    result, error = document_service.publish(document_id, get_jwt_identity())
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Document published')


@document_bp.route('/<document_id>/confirm-receipt', methods=['POST'])
@jwt_required()
def confirm_receipt(document_id):
    result, error = document_service.confirm_receipt(document_id, get_jwt_identity())
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Receipt confirmed')
