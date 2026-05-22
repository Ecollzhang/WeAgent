from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from app.repositories.user_repo import user_repo


class AuthService:
    """Authentication & authorization service."""

    def register(self, username, email, password):
        """Register a new user."""
        if user_repo.username_exists(username):
            return None, 'Username already exists'

        if user_repo.email_exists(email):
            return None, 'Email already exists'

        password_hash = generate_password_hash(password)
        user = user_repo.create(
            username=username,
            email=email,
            password_hash=password_hash
        )

        # Copy system categories and agents as user-specific records
        from app.services.agent_service import agent_service
        agent_service.copy_default_data_to_user(user.id)

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        return {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }, None

    def login(self, username, password):
        """Authenticate user and return tokens."""
        user = user_repo.get_by_username(username)
        if not user:
            return None, 'Invalid username or password'

        if not check_password_hash(user.password_hash, password):
            return None, 'Invalid username or password'

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        return {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }, None

    def get_profile(self, user_id):
        """Get user profile."""
        user = user_repo.get_by_id(user_id)
        if not user:
            return None, 'User not found'
        return user.to_dict(), None

    def update_profile(self, user_id, **kwargs):
        """Update user profile."""
        user = user_repo.get_by_id(user_id)
        if not user:
            return None, 'User not found'
        allowed = {'username', 'email', 'avatar_url'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(user, k, v)
        user.save()
        return user.to_dict(), None

    def refresh_token(self, identity):
        """Generate a new access token."""
        access_token = create_access_token(identity=identity)
        return {'access_token': access_token}, None


auth_service = AuthService()
