from app.models import BaseModel, db


class UserModelConfig(BaseModel):
    """Per-user model configuration saved from Settings."""
    __tablename__ = 'user_model_configs'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'),
                        nullable=False, unique=True, index=True)
    api_key = db.Column(db.Text, nullable=True)
    base_url = db.Column(db.String(500), nullable=True)
    model = db.Column(db.String(100), nullable=False, default='claude-3.5-sonnet')
    temperature = db.Column(db.Float, nullable=False, default=0.7)
    max_tokens = db.Column(db.Integer, nullable=False, default=4096)

    user = db.relationship('User', backref=db.backref('model_config', uselist=False),
                           lazy='select')
