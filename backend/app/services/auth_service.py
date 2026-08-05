from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from app.repositories.user_repo import user_repo

import base64
import os
import re
import uuid
from flask import current_app


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
        print(f"Attempting login for username/email: {username}")
        user = user_repo.get_by_username(username)
        print(f"User found by username: {user}")
        if not user and '@' in str(username or ''):
            user = user_repo.get_by_email(username)
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

    def get_public_profiles(self, user_ids):
        """Return the small, non-sensitive account projection used by domains."""
        from app.models.user import User

        ids = list(dict.fromkeys(str(value) for value in user_ids if value))
        if not ids:
            return []
        users = User.query.filter(User.id.in_(ids)).all()
        by_id = {user.id: user for user in users}
        return [
            {
                'id': user.id,
                'username': user.username,
                'avatar_url': user.avatar_url or '',
            }
            for user_id in ids
            for user in [by_id.get(user_id)]
            if user is not None
        ]

    def update_profile(self, user_id, **kwargs):
        """Update user profile."""
        user = user_repo.get_by_id(user_id)
        if not user:
            return None, 'User not found'
        avatar_url = kwargs.get('avatar_url')
        if isinstance(avatar_url, str) and avatar_url.startswith('data:image/'):
            try:
                kwargs['avatar_url'] = self._store_avatar_data_url(avatar_url)
            except ValueError as exc:
                return None, str(exc)
        allowed = {'username', 'email', 'avatar_url'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(user, k, v)
        user.save()
        return user.to_dict(), None

    def _store_avatar_data_url(self, data_url):
        match = re.match(r'^data:image/(png|jpe?g|gif|webp);base64,(.+)$', data_url, re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError('Invalid avatar image data')

        ext = match.group(1).lower()
        if ext == 'jpeg':
            ext = 'jpg'
        encoded = re.sub(r'\s+', '', match.group(2))
        if len(encoded) > 3 * 1024 * 1024:
            raise ValueError('Avatar image is too large')

        try:
            content = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError('Invalid avatar image data') from exc

        if len(content) > 2 * 1024 * 1024:
            raise ValueError('Avatar image is too large')

        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'{uuid.uuid4().hex}.{ext}'
        with open(os.path.join(upload_dir, filename), 'wb') as file:
            file.write(content)
        return f'/uploads/{filename}'

    def list_users(self):
        """List all users (id, username, role)."""
        users = user_repo.get_all()
        return {
            'items': [{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role, 'avatar_url': u.avatar_url} for u in users],
            'total': len(users),
        }, None

    def refresh_token(self, identity):
        """Generate a new access token."""
        access_token = create_access_token(identity=identity)
        return {'access_token': access_token}, None


auth_service = AuthService()
