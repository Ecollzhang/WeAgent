from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response
from app.schemas.user_schema import RegisterSchema, LoginSchema
from app.services.auth_service import auth_service
from marshmallow import ValidationError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        schema = RegisterSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = auth_service.register(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Registration successful', code=201)


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and get JWT tokens."""
    try:
        schema = LoginSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = auth_service.login(
        username=data['username'],
        password=data['password']
    )

    if error:
        return error_response(error, code=401)

    return success_response(result, message='Login successful')


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Get current user profile."""
    user_id = get_jwt_identity()
    result, error = auth_service.get_profile(user_id)

    if error:
        return error_response(error, code=404)

    return success_response(result)


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile."""
    user_id = get_jwt_identity()
    data = request.json or {}
    result, error = auth_service.update_profile(user_id, **data)
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Profile updated')


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    identity = get_jwt_identity()
    result, error = auth_service.refresh_token(identity)

    if error:
        return error_response(error, code=401)

    return success_response(result)
