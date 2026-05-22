from flask_jwt_extended import get_jwt_identity


def get_current_user_id():
    """Get current user ID from JWT token."""
    return get_jwt_identity()
