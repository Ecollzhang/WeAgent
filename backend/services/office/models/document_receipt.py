"""Delivery and acknowledgement records for published office documents."""
from extensions import db
from models.base import OfficeBaseModel


class DocumentReceipt(OfficeBaseModel):
    __tablename__ = 'office_document_receipts'

    document_id = db.Column(db.String(36), nullable=False, index=True)
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    recipient_id = db.Column(db.String(36), nullable=False, index=True)
    recipient_name = db.Column(db.String(100), default='')
    read_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
