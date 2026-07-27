import uuid
from datetime import datetime
from app import db
from app.utils.timezone import beijing_now, format_beijing


class BaseModel(db.Model):
    """Abstract base model with common fields."""
    __abstract__ = True

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=beijing_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=beijing_now, onupdate=beijing_now, nullable=False)

    def to_dict(self):
        """Convert model to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = format_beijing(value)
            else:
                result[column.name] = value
        return result

    def save(self):
        """Save instance to database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Delete instance from database."""
        db.session.delete(self)
        db.session.commit()


from app.models.toolset_category import ToolsetCategory  # noqa: E402,F401
from app.models.capability import (  # noqa: E402,F401
    AgentCapabilityBinding,
    Capability,
    CapabilityCallRecord,
    CapabilityImportJob,
    CapabilitySecurityAudit,
    CapabilityVersion,
    CapabilityVersionAsset,
    PluginInstallRecord,
    SkillRevisionDraft,
)
from app.models.tool_provider_config import ToolProviderConfig  # noqa: E402,F401
from app.models.workspace import Workspace  # noqa: E402,F401
from app.models.grayscale_config import GrayscaleConfig  # noqa: E402,F401
