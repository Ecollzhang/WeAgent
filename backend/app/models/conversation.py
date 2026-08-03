from app.models import BaseModel, db


class Conversation(BaseModel):
    """Conversation/Dialog model."""
    __tablename__ = 'conversations'

    title = db.Column(db.String(200), nullable=False, default='New Conversation')
    type = db.Column(db.Enum('single', 'group', name='conversation_type'),
                     nullable=False, default='single')
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    sandbox_session_id = db.Column(db.String(100), nullable=True, index=True)
    sandbox_container_id = db.Column(db.String(128), nullable=True)
    sandbox_host_port = db.Column(db.Integer, nullable=True)
    sandbox_status = db.Column(db.Enum('pending', 'running', 'stopped', 'error',
                                       name='sandbox_status'),
                               nullable=False, default='pending')
    workspace_id = db.Column(db.String(36), db.ForeignKey('workspaces.id',
                                ondelete='SET NULL'), nullable=True)
    kb_domain = db.Column(db.String(20), nullable=False, default='')
    sandbox_server_fallback = db.Column(db.Boolean, nullable=False, default=False)
    sandbox_agent_adapters = db.Column(db.JSON, nullable=False, default=dict)
    kb_document_ids = db.Column(db.JSON, nullable=True, comment='Selected KB document IDs for filtering')
    services = db.Column(db.JSON, nullable=True, comment='启用的领域服务列表, e.g. ["rd","rag"]')
    project_id = db.Column(db.String(36), nullable=True, comment='关联的RD项目ID，NULL=全局视角')
    last_active_at = db.Column(db.DateTime, nullable=True)
    stopped_at = db.Column(db.DateTime, nullable=True)
    sandbox_generation = db.Column(db.Integer, nullable=False, default=1)
    sandbox_expires_at = db.Column(db.DateTime, nullable=True, index=True)
    sandbox_snapshot_path = db.Column(db.String(500), nullable=True)
    sandbox_snapshot_sha256 = db.Column(db.String(64), nullable=True)
    sandbox_snapshot_size = db.Column(db.Integer, nullable=True)
    sandbox_snapshot_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    participants = db.relationship('ConversationParticipant', backref='conversation',
                                   lazy='joined', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='conversation',
                               lazy='dynamic', cascade='all, delete-orphan',
                               order_by='Message.created_at')


class ConversationParticipant(BaseModel):
    """Conversation participant model."""
    __tablename__ = 'conversation_participants'

    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'),
                                nullable=False)
    participant_type = db.Column(db.Enum('user', 'agent', name='participant_type'),
                                 nullable=False)
    participant_id = db.Column(db.String(36), nullable=False)
    participant_name = db.Column(db.String(200), default='')
    participant_avatar = db.Column(db.String(500), default='')
    participant_color = db.Column(db.String(20), default='')
    joined_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'participant_type', 'participant_id',
                            name='uq_conversation_participant'),
    )
