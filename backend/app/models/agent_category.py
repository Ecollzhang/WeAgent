from app.models import BaseModel, db


class AgentCategory(BaseModel):
    """Agent category/class for organizing agents."""
    __tablename__ = 'agent_categories'

    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default='el-icon-folder')
    color = db.Column(db.String(20), default='#4080ff')
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
