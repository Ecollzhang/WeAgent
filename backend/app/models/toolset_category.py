from app.models import BaseModel, db


class ToolsetCategory(BaseModel):
    """User-facing category for organizing Skill, MCP, Plugin, and Tool capabilities."""
    __tablename__ = "toolset_categories"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), nullable=False, index=True)
    icon = db.Column(db.String(50), default="el-icon-folder")
    color = db.Column(db.String(20), default="#4080ff")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_builtin = db.Column(db.Boolean, nullable=False, default=False)

    owner = db.relationship("User", backref="toolset_categories", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("user_id", "slug", name="uq_toolset_category_user_slug"),
    )
