"""Admin authorization decorator."""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request


def admin_required():
    """Decorator that requires the current user to have role='admin'.

    Must be used AFTER @jwt_required().

    Usage:
        @bp.route('/admin/xxx', methods=['POST'])
        @jwt_required()
        @admin_required()
        def admin_endpoint():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            from app.models.user import User
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                return jsonify({
                    'code': 403,
                    'message': 'Admin access required',
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
