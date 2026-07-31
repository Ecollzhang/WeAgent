"""Meeting model."""
from extensions import db
from models.base import OfficeBaseModel


class Meeting(OfficeBaseModel):
    """A workspace-scoped office meeting and its recorded outcome."""
    __tablename__ = 'office_meetings'

    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    organizer_id = db.Column(db.String(36), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    agenda = db.Column(db.Text, default='')
    participants = db.Column(db.JSON, default=list)
    location = db.Column(db.String(200), default='')
    meeting_link = db.Column(db.String(1000), default='')
    start_time = db.Column(db.DateTime, nullable=True, index=True)
    end_time = db.Column(db.DateTime, nullable=True)
    transcript = db.Column(db.Text, default='')
    minutes = db.Column(db.Text, default='')
    resolutions = db.Column(db.JSON, default=list)
    status = db.Column(
        db.Enum('scheduled', 'ongoing', 'completed', 'cancelled', name='office_meeting_status'),
        default='scheduled', nullable=False, index=True,
    )

    action_items = db.relationship(
        'ActionItem', backref='meeting', lazy='dynamic', cascade='all, delete-orphan'
    )
