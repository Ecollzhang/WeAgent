from app.models import BaseModel, db


class Agent(BaseModel):
    """Agent model - represents an AI agent."""
    __tablename__ = 'agents'

    name = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(500), default='')
    avatar_color = db.Column(db.String(20), default='')
    capability_tags = db.Column(db.JSON, default=list)
    agent_type = db.Column(db.Enum('external', 'custom', name='agent_type'),
                           nullable=False, default='external')
    adapter_name = db.Column(db.String(50), nullable=False, default='claude')
    config = db.Column(db.JSON, default=dict)
    system_prompt = db.Column(db.Text, default='')
    skill = db.Column(db.Text, default='')
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    class_id = db.Column(db.String(36), db.ForeignKey('agent_categories.id'), nullable=True)
    domain = db.Column(db.String(50), default='rd', comment='rd / edu / office')
    tool_ids = db.Column(db.JSON, default=list)
    is_public = db.Column(db.Boolean, default=True)

    # Relationships
    creator = db.relationship('User', backref='created_agents', lazy='select',
                              foreign_keys=[created_by])
    owner = db.relationship('User', backref='owned_agents', lazy='select',
                            foreign_keys=[user_id])

    def to_dict(self):
        data = super().to_dict()
        data['is_system'] = self.id == 'moderator'
        data['read_only'] = self.id == 'moderator'
        # Mask sensitive config in API responses
        if 'config' in data and data['config']:
            safe_config = data['config'].copy()
            if 'api_key' in safe_config:
                safe_config['api_key'] = '****' + safe_config['api_key'][-4:] if len(safe_config['api_key']) > 4 else '****'
            data['config'] = safe_config
        return data
