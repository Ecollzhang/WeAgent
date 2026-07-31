"""Office dashboard REST API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils.response import error_response, success_response
from services.dashboard_service import dashboard_service


dashboard_bp = Blueprint('office_dashboard', __name__)


@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary():
    result, error = dashboard_service.summary(
        get_jwt_identity(), request.args.get('workspace_id', '').strip()
    )
    if error:
        return error_response(error, code=400)
    return success_response(result)
