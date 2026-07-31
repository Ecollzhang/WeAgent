"""Minimal user directory used when inviting real accounts to an office workspace."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.models.user import User
from app.utils.response import success_response

user_directory_bp = Blueprint('user_directory', __name__)


@user_directory_bp.route('/api/user-directory', methods=['GET'])
@jwt_required()
def search_users():
    query = (request.args.get('query') or '').strip()
    users = User.query
    if query:
        users = users.filter(User.username.like(f'%{query}%'))
    return success_response([{'id': item.id, 'username': item.username, 'avatar_url': item.avatar_url}
                             for item in users.order_by(User.username).limit(20).all()])
