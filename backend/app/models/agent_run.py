from app.models import BaseModel, db


class AgentRun(BaseModel):
    """Execution state for one agent in one conversation round."""
    __tablename__ = 'agent_runs'

    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'),
                                nullable=False, index=True)
    round_id = db.Column(db.String(36), nullable=False, index=True)
    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'),
                           nullable=True, index=True)
    agent_id = db.Column(db.String(36), nullable=False, index=True)
    sandbox_session_id = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(db.Enum('pending', 'running', 'done', 'error', 'stopped',
                               name='agent_run_status'),
                       nullable=False, default='pending')
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    error = db.Column(db.Text, nullable=True)
    last_seq = db.Column(db.Integer, nullable=False, default=0)
    meta = db.Column(db.JSON, nullable=True)

    conversation = db.relationship('Conversation', backref='agent_runs', lazy='select')
    message = db.relationship('Message', backref=db.backref('agent_run', uselist=False),
                              lazy='select')
