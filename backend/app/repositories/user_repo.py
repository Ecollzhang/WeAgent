from app.repositories.base_repo import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository):
    """User repository with user-specific queries."""

    def __init__(self):
        super().__init__(User)

    def get_by_username(self, username):
        """Get user by username."""
        return User.query.filter_by(username=username).first()

    def get_by_email(self, email):
        """Get user by email."""
        return User.query.filter_by(email=email).first()

    def username_exists(self, username):
        """Check if username exists."""
        return User.query.filter_by(username=username).first() is not None

    def email_exists(self, email):
        """Check if email exists."""
        return User.query.filter_by(email=email).first() is not None


user_repo = UserRepository()
