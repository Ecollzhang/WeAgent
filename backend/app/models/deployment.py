from app.models import BaseModel, db


class Deployment(BaseModel):
    __tablename__ = 'deployments'

    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    artifact_id = db.Column(db.String(36), db.ForeignKey('artifacts.id'), nullable=True)
    status = db.Column(db.Enum('pending', 'deploying', 'success', 'failed', name='deploy_status'), nullable=False, default='pending')
    provider = db.Column(db.String(50), default='mock')
    preview_url = db.Column(db.String(500), default='')
    deploy_url = db.Column(db.String(500), default='')
    progress = db.Column(db.Integer, default=0)
    logs = db.Column(db.JSON, default=list)
    error = db.Column(db.Text, nullable=True)
    source_type = db.Column(db.String(50), default='webpage')
