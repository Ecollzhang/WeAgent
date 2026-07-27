from app.models import BaseModel, db


class User(BaseModel):
    """User model."""
    __tablename__ = 'users'

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(500), default='')
    role = db.Column(db.String(20), nullable=False, default='user', comment='admin / user')

    # Relationships
    conversations = db.relationship('Conversation', backref='owner', lazy='dynamic',
                                    foreign_keys='Conversation.owner_id')

    def to_dict(self):
        data = super().to_dict()
        # Never expose password hash
        data.pop('password_hash', None)
        return data

    @property
    def is_admin(self):
        return self.role == 'admin'
