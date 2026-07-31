"""Shared model helpers for the office domain."""
import uuid
from datetime import date, datetime

from extensions import db


class OfficeBaseModel(db.Model):
    """Abstract model with UUID primary keys and JSON-ready serialization."""
    __abstract__ = True

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        """Serialize a record for the domain REST API."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, (datetime, date)):
                result[column.name] = value.isoformat(sep=' ', timespec='seconds')
            else:
                result[column.name] = value
        return result
