from app.models import BaseModel, db


CAPABILITY_TYPES = ("skill", "tool", "mcp", "plugin")
VERSION_POLICIES = ("pinned", "follow_latest")
CALL_STATUSES = ("started", "completed", "failed")
DRAFT_STATUSES = ("pending_review", "published", "forked", "rejected")
PLUGIN_INSTALL_STATUSES = ("installed", "failed", "removed")


class Capability(BaseModel):
    """Reusable Skill, Tool, MCP, or Plugin definition."""
    __tablename__ = "capabilities"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    type = db.Column(db.Enum(*CAPABILITY_TYPES, name="capability_type"),
                     nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, default="")
    source = db.Column(db.String(50), nullable=False, default="user", index=True)
    source_ref = db.Column(db.String(500), default="")
    is_builtin = db.Column(db.Boolean, nullable=False, default=False)
    latest_version_id = db.Column(db.String(36), nullable=True, index=True)

    versions = db.relationship(
        "CapabilityVersion",
        back_populates="capability",
        cascade="all, delete-orphan",
        lazy="select",
    )
    owner = db.relationship("User", backref="capabilities", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("user_id", "slug", name="uq_capability_user_slug"),
    )


class CapabilityVersion(BaseModel):
    """Immutable version of a capability."""
    __tablename__ = "capability_versions"

    capability_id = db.Column(db.String(36), db.ForeignKey("capabilities.id"),
                              nullable=False, index=True)
    version = db.Column(db.String(50), nullable=False, default="1.0.0")
    content = db.Column(db.Text, default="")
    manifest = db.Column(db.JSON, default=dict)
    permissions = db.Column(db.JSON, default=dict)
    meta = db.Column(db.JSON, default=dict)
    checksum = db.Column(db.String(128), default="")
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    capability = db.relationship("Capability", back_populates="versions", lazy="select")
    creator = db.relationship("User", backref="capability_versions", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("capability_id", "version", name="uq_capability_version"),
    )


class AgentCapabilityBinding(BaseModel):
    """Default capability grant for an Agent."""
    __tablename__ = "agent_capability_bindings"

    agent_id = db.Column(db.String(36), db.ForeignKey("agents.id"),
                         nullable=False, index=True)
    capability_id = db.Column(db.String(36), db.ForeignKey("capabilities.id"),
                              nullable=False, index=True)
    capability_version_id = db.Column(db.String(36), db.ForeignKey("capability_versions.id"),
                                      nullable=False, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    version_policy = db.Column(db.Enum(*VERSION_POLICIES, name="capability_version_policy"),
                               nullable=False, default="pinned")
    granted_permissions = db.Column(db.JSON, default=list)
    authorization_snapshot = db.Column(db.JSON, default=dict)

    agent = db.relationship("Agent", backref=db.backref("capability_bindings", lazy="select"))
    capability = db.relationship("Capability", lazy="select")
    capability_version = db.relationship("CapabilityVersion", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("agent_id", "capability_id", name="uq_agent_capability"),
    )


class CapabilityCallRecord(BaseModel):
    """Audit record for a real Tool or MCP call."""
    __tablename__ = "capability_call_records"

    session_id = db.Column(db.String(100), nullable=False, index=True)
    run_id = db.Column(db.String(100), nullable=True, index=True)
    agent_id = db.Column(db.String(36), nullable=False, index=True)
    capability_id = db.Column(db.String(36), db.ForeignKey("capabilities.id"),
                              nullable=False, index=True)
    capability_version_id = db.Column(db.String(36), db.ForeignKey("capability_versions.id"),
                                      nullable=False, index=True)
    call_type = db.Column(db.String(30), nullable=False, default="tool", index=True)
    tool_name = db.Column(db.String(160), nullable=False, default="")
    permissions_used = db.Column(db.JSON, default=list)
    input_summary = db.Column(db.JSON, default=dict)
    output_summary = db.Column(db.JSON, default=dict)
    status = db.Column(db.Enum(*CALL_STATUSES, name="capability_call_status"),
                       nullable=False, default="started", index=True)
    error = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    capability = db.relationship("Capability", lazy="select")
    capability_version = db.relationship("CapabilityVersion", lazy="select")


class PluginInstallRecord(BaseModel):
    """Manifest-only Plugin installation record for v1."""
    __tablename__ = "plugin_install_records"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"),
                        nullable=False, index=True)
    plugin_capability_id = db.Column(db.String(36), db.ForeignKey("capabilities.id"),
                                     nullable=False, index=True)
    plugin_version_id = db.Column(db.String(36), db.ForeignKey("capability_versions.id"),
                                  nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False, default="npx", index=True)
    source_ref = db.Column(db.String(500), default="")
    package_name = db.Column(db.String(240), default="")
    package_version = db.Column(db.String(80), default="")
    status = db.Column(db.Enum(*PLUGIN_INSTALL_STATUSES, name="plugin_install_status"),
                       nullable=False, default="installed", index=True)
    manifest = db.Column(db.JSON, default=dict)
    included_capabilities = db.Column(db.JSON, default=list)

    owner = db.relationship("User", backref="plugin_install_records", lazy="select")
    plugin_capability = db.relationship(
        "Capability",
        foreign_keys=[plugin_capability_id],
        lazy="select",
    )
    plugin_version = db.relationship(
        "CapabilityVersion",
        foreign_keys=[plugin_version_id],
        lazy="select",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "plugin_capability_id",
            "plugin_version_id",
            name="uq_plugin_install_version",
        ),
    )


class SkillRevisionDraft(BaseModel):
    """Agent-written Skill change waiting for user review."""
    __tablename__ = "skill_revision_drafts"

    source_skill_id = db.Column(db.String(36), db.ForeignKey("capabilities.id"),
                                nullable=False, index=True)
    source_version_id = db.Column(db.String(36), db.ForeignKey("capability_versions.id"),
                                  nullable=False, index=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    agent_id = db.Column(db.String(36), nullable=False, index=True)
    diff = db.Column(db.JSON, default=dict)
    full_markdown = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.Enum(*DRAFT_STATUSES, name="skill_revision_draft_status"),
                       nullable=False, default="pending_review", index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    source_skill = db.relationship("Capability", lazy="select")
    source_version = db.relationship("CapabilityVersion", lazy="select")
