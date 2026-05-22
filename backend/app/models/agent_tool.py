from app.models import BaseModel, db


class AgentTool(BaseModel):
    """Agent tool model — built-in tools + user custom tools."""
    __tablename__ = 'agent_tools'

    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='tool_custom')
    icon = db.Column(db.String(50), default='el-icon-setting')
    color = db.Column(db.String(20), default='#a0aec0')
    description = db.Column(db.Text, default='')
    params = db.Column(db.JSON, default=dict)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    is_builtin = db.Column(db.Boolean, default=False)
