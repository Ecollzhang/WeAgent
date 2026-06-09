from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.toolset_category_service import toolset_category_service
from app.utils.response import error_response, success_response


toolset_bp = Blueprint("toolsets", __name__)


@toolset_bp.route("/categories", methods=["GET"])
@jwt_required()
def list_categories():
    user_id = get_jwt_identity()
    result, error = toolset_category_service.list_categories(user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@toolset_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    user_id = get_jwt_identity()
    data = request.json or {}
    result, error = toolset_category_service.create_category(
        user_id=user_id,
        name=data.get("name", ""),
        icon=data.get("icon"),
        color=data.get("color"),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message="Toolset category created", code=201)


@toolset_bp.route("/categories/<category_id>", methods=["PUT"])
@jwt_required()
def update_category(category_id):
    user_id = get_jwt_identity()
    result, error = toolset_category_service.update_category(
        user_id,
        category_id,
        **(request.json or {}),
    )
    if error:
        return error_response(error, code=404)
    return success_response(result, message="Toolset category updated")


@toolset_bp.route("/categories/<category_id>", methods=["DELETE"])
@jwt_required()
def delete_category(category_id):
    user_id = get_jwt_identity()
    result, error = toolset_category_service.delete_category(user_id, category_id)
    if error:
        code = 400 if "Built-in" in error else 404
        return error_response(error, code=code)
    return success_response(result, message="Toolset category deleted")
