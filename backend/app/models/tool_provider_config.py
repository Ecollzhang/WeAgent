from app.models import BaseModel, db


TOOL_PROVIDER_TYPES = ("mcp", "http", "model", "database")
TOOL_PROVIDER_CONFIG_STATUSES = ("draft", "valid", "invalid", "disabled")


class ToolProviderConfig(BaseModel):
    """User-managed provider profile for a configurable built-in Tool."""
    __tablename__ = "tool_provider_configs"

    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    capability_id = db.Column(
        db.String(36),
        db.ForeignKey("capabilities.id"),
        nullable=False,
        index=True,
    )
    profile_name = db.Column(db.String(120), nullable=False, default="Default")
    provider_type = db.Column(
        db.Enum(*TOOL_PROVIDER_TYPES, name="tool_provider_type"),
        nullable=False,
        index=True,
    )
    config = db.Column(db.JSON, default=dict)
    secret_refs = db.Column(db.JSON, default=list)
    status = db.Column(
        db.Enum(*TOOL_PROVIDER_CONFIG_STATUSES, name="tool_provider_config_status"),
        nullable=False,
        default="draft",
        index=True,
    )
    last_test_status = db.Column(db.String(30), nullable=False, default="")
    last_test_error = db.Column(db.Text, nullable=False, default="")
    last_test_result = db.Column(db.JSON, default=dict)

    owner = db.relationship("User", backref="tool_provider_configs", lazy="select")
    capability = db.relationship("Capability", backref="provider_configs", lazy="select")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "capability_id",
            "profile_name",
            name="uq_tool_provider_config_profile",
        ),
    )
