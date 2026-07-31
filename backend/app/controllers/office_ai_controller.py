"""Authenticated AI drafting endpoints for office pages."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.office_ai_service import office_ai_service
from app.utils.response import error_response, success_response


office_ai_bp = Blueprint('office_ai', __name__)


@office_ai_bp.route('/meeting-draft', methods=['POST'])
@jwt_required()
def meeting_draft():
    result, service_error = office_ai_service.meeting_draft(
        get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if service_error:
        return error_response(service_error, code=400)
    return success_response(result, message='Meeting draft generated')


@office_ai_bp.route('/document-draft', methods=['POST'])
@jwt_required()
def document_draft():
    result, service_error = office_ai_service.document_draft(
        get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if service_error:
        return error_response(service_error, code=400)
    return success_response(result, message='Document draft generated')


@office_ai_bp.route('/weekly-draft', methods=['POST'])
@jwt_required()
def weekly_draft():
    result, service_error = office_ai_service.weekly_draft(
        get_jwt_identity(), request.get_json(silent=True) or {}
    )
    if service_error:
        return error_response(service_error, code=400)
    return success_response(result, message='Weekly report draft generated')
