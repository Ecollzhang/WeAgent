"""Approval flow model."""
from extensions import db
from models.base import OfficeBaseModel


class Approval(OfficeBaseModel):
    """A serial approval request linked to an office document."""
    __tablename__ = 'office_approvals'

    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    document_id = db.Column(db.String(36), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    approval_type = db.Column(db.String(50), default='document')
    initiator_id = db.Column(db.String(36), nullable=False, index=True)
    current_step = db.Column(db.Integer, default=1, nullable=False)
    steps = db.Column(db.JSON, default=list)
    history = db.Column(db.JSON, default=list)
    status = db.Column(
        db.Enum('pending', 'approved', 'rejected', 'cancelled', name='office_approval_status'),
        default='pending', nullable=False, index=True,
    )
