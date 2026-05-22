from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response
from app.services.tool_service import tool_service

tool_bp = Blueprint('tools', __name__)


@tool_bp.route('', methods=['GET'])
@jwt_required()
def list_tools():
    """Get all tools (built-in + user custom)."""
    user_id = get_jwt_identity()
    result, error = tool_service.get_tools(user_id=user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@tool_bp.route('/<tool_id>', methods=['GET'])
@jwt_required()
def get_tool(tool_id):
    """Get single tool detail."""
    result, error = tool_service.get_tool_detail(tool_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@tool_bp.route('', methods=['POST'])
@jwt_required()
def create_tool():
    """Create a custom tool."""
    user_id = get_jwt_identity()
    data = request.json or {}
    name = data.get('name', '').strip()
    value = data.get('value', '').strip()
    if not name or not value:
        return error_response('Name and value are required', code=400)
    result, error = tool_service.create_tool(
        user_id=user_id,
        name=name,
        value=value,
        category=data.get('category', 'tool_custom'),
        icon=data.get('icon', 'el-icon-setting'),
        color=data.get('color', '#a0aec0'),
        description=data.get('description', ''),
        params=data.get('params'),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Tool created', code=201)


@tool_bp.route('/<tool_id>', methods=['PUT'])
@jwt_required()
def update_tool(tool_id):
    """Update a custom tool (owner only)."""
    user_id = get_jwt_identity()
    result, error = tool_service.update_tool(tool_id, user_id, **request.json)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Tool updated')


@tool_bp.route('/<tool_id>', methods=['DELETE'])
@jwt_required()
def delete_tool(tool_id):
    """Delete a custom tool (owner only)."""
    user_id = get_jwt_identity()
    result, error = tool_service.delete_tool(tool_id, user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Tool deleted')
