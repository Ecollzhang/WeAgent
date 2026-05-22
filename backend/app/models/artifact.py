from app.models import BaseModel, db


class Artifact(BaseModel):
    """Artifact model - stores generated artifacts (code, webpages, docs, etc.)."""
    __tablename__ = 'artifacts'

    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=True)
    artifact_type = db.Column(
        db.Enum('code', 'webpage', 'document', 'ppt', 'diff', name='artifact_type'),
        nullable=False, default='code'
    )
    title = db.Column(db.String(200), nullable=False, default='Untitled')
    content = db.Column(db.Text, default='')
    language = db.Column(db.String(50), default='')
    preview_url = db.Column(db.String(500), default='')
    deploy_url = db.Column(db.String(500), default='')
    version = db.Column(db.Integer, default=1)
