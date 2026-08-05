"""Office schedule model."""
from extensions import db
from models.base import OfficeBaseModel


class Schedule(OfficeBaseModel):
    """A personal or team calendar event in an office workspace."""
    __tablename__ = 'office_schedules'

    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    event_type = db.Column(
        db.Enum('meeting', 'task', 'reminder', 'other', name='office_schedule_type'),
        default='task', nullable=False,
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    priority = db.Column(
        db.Enum('low', 'medium', 'high', name='office_schedule_priority'), default='medium'
    )
    status = db.Column(
        db.Enum('pending', 'in_progress', 'done', 'cancelled', name='office_schedule_status'),
        default='pending', nullable=False, index=True,
    )
    meeting_id = db.Column(db.String(36), nullable=True, index=True)
    document_id = db.Column(db.String(36), nullable=True, index=True)
    action_item_id = db.Column(db.String(36), nullable=True, index=True)
