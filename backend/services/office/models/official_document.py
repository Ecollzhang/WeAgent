"""Official document model."""
from extensions import db
from models.base import OfficeBaseModel


class OfficialDocument(OfficeBaseModel):
    """A workspace-scoped document with a lightweight approval lifecycle."""
    __tablename__ = 'office_documents'

    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    meeting_id = db.Column(db.String(36), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    document_type = db.Column(
        db.Enum('notice', 'report', 'request', 'letter', 'minutes', 'other', name='office_document_type'),
        nullable=False,
    )
    content = db.Column(db.Text, default='')
    recipients = db.Column(db.JSON, default=list)
    approvers = db.Column(db.JSON, default=list)
    template_id = db.Column(db.String(36), nullable=True)
    status = db.Column(
        db.Enum('draft', 'reviewing', 'approved', 'published', 'archived', name='office_document_status'),
        default='draft', nullable=False, index=True,
    )
    reviewer_id = db.Column(db.String(36), nullable=True)
    review_comment = db.Column(db.Text, default='')
    published_at = db.Column(db.DateTime, nullable=True)
