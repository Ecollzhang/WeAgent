from app.models import BaseModel, db


class Workspace(BaseModel):
    """Domain workspace model — 领域工作空间."""
    __tablename__ = 'workspaces'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False)
    domain = db.Column(db.String(50), nullable=False, comment='rd / edu / office')
    sub_role = db.Column(db.String(20), default='', comment='edu 领域区分: teacher / student')
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(50), default='default')
    sort_order = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('active', 'archived', name='workspace_status'),
                       default='active')

    # Relationships
    conversations = db.relationship('Conversation', backref='workspace',
                                    lazy='dynamic')

    def to_dict(self):
        result = super().to_dict()
        result['conversation_count'] = self.conversations.count()
        return result
