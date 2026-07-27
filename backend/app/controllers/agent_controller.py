from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response
from app.schemas.agent_schema import CreateAgentSchema
from app.services.agent_service import agent_service
from marshmallow import ValidationError

agent_bp = Blueprint('agents', __name__)


# ── Agent CRUD (user-scoped) ─────────────────────────────────────────

@agent_bp.route('', methods=['GET'])
@jwt_required()
def list_agents():
    """Get agents for current user. Optional ?class_id=xxx&domain=xxx filter."""
    user_id = get_jwt_identity()
    class_id = request.args.get('class_id')
    domain = request.args.get('domain')
    result, error = agent_service.get_user_agents(user_id, class_id=class_id, domain=domain)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@agent_bp.route('/<agent_id>', methods=['GET'])
@jwt_required()
def get_agent(agent_id):
    """Get agent detail."""
    result, error = agent_service.get_agent_detail(agent_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@agent_bp.route('', methods=['POST'])
@jwt_required()
def create_agent():
    """Create a custom agent."""
    user_id = get_jwt_identity()

    try:
        schema = CreateAgentSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = agent_service.create_agent(
        user_id=user_id,
        name=data['name'],
        capability_tags=data.get('capability_tags', []),
        agent_type=data.get('agent_type', 'custom'),
        adapter_name=data.get('adapter_name', 'claude'),
        config=data.get('config', {}),
        system_prompt=data.get('system_prompt', ''),
        skill=data.get('skill', ''),
        avatar_color=data.get('avatar_color', ''),
        avatar_url=data.get('avatar_url', ''),
        class_id=data.get('class_id'),
        is_public=data.get('is_public', False),
        tool_ids=data.get('tool_ids', []),
        capability_bindings=data.get('capability_bindings', []),
        domain=data.get('domain'),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Agent created', code=201)


@agent_bp.route('/<agent_id>', methods=['PUT'])
@jwt_required()
def update_agent(agent_id):
    """Update an agent (owner only)."""
    user_id = get_jwt_identity()
    result, error = agent_service.update_agent(agent_id, user_id, **request.json)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Agent updated')


@agent_bp.route('/<agent_id>', methods=['DELETE'])
@jwt_required()
def delete_agent(agent_id):
    """Delete an agent (owner only)."""
    user_id = get_jwt_identity()
    result, error = agent_service.delete_agent(agent_id, user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Agent deleted')


# ── Category CRUD (user-scoped) ──────────────────────────────────────

@agent_bp.route('/categories', methods=['GET'])
@jwt_required()
def list_categories():
    """Get categories for current user. Optional ?domain=xxx filter."""
    user_id = get_jwt_identity()
    domain = request.args.get('domain')
    result, error = agent_service.get_categories(user_id, domain=domain)
    if error:
        return error_response(error, code=400)
    return success_response(result)


@agent_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_category():
    """Create a category for current user."""
    user_id = get_jwt_identity()
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return error_response('Category name is required', code=400)
    result, error = agent_service.create_category(
        user_id=user_id,
        name=name,
        icon=data.get('icon'),
        color=data.get('color'),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Category created', code=201)


@agent_bp.route('/categories/<category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """Update a category (owner only)."""
    user_id = get_jwt_identity()
    result, error = agent_service.update_category(category_id, user_id, **request.json)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Category updated')


@agent_bp.route('/categories/<category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category (owner only)."""
    user_id = get_jwt_identity()
    result, error = agent_service.delete_category(category_id, user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Category deleted')
