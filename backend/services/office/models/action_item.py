"""Meeting action item model."""
from extensions import db
from models.base import OfficeBaseModel


class ActionItem(OfficeBaseModel):
    """A trackable responsibility generated from a meeting outcome."""
    __tablename__ = 'office_action_items'

    meeting_id = db.Column(
        db.String(36), db.ForeignKey('office_meetings.id', ondelete='CASCADE'), nullable=False,
        index=True,
    )
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    creator_id = db.Column(db.String(36), nullable=False, index=True)
    assignee_id = db.Column(db.String(36), default='', index=True)
    assignee_name = db.Column(db.String(100), default='')
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    due_date = db.Column(db.DateTime, nullable=True, index=True)
    priority = db.Column(
        db.Enum('low', 'medium', 'high', name='office_action_priority'), default='medium'
    )
    status = db.Column(
        db.Enum('pending', 'in_progress', 'done', 'cancelled', name='office_action_status'),
        default='pending', nullable=False, index=True,
    )
    schedule_id = db.Column(db.String(36), nullable=True, index=True)
