"""Official document template model."""
from extensions import db
from models.base import OfficeBaseModel


class DocumentTemplate(OfficeBaseModel):
    """Reusable document template for a workspace."""
    __tablename__ = 'office_doc_templates'

    workspace_id = db.Column(db.String(36), nullable=True, index=True)
    creator_id = db.Column(db.String(36), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    document_type = db.Column(
        db.Enum('notice', 'report', 'request', 'letter', 'minutes', 'other', name='office_template_type'),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False)
    format_spec = db.Column(db.Text, default='')
    is_system = db.Column(db.Boolean, default=False, nullable=False)
