"""Shared access to a workspace owned by another registered account."""
from app.models import BaseModel, db


class WorkspaceMember(BaseModel):
    __tablename__ = 'workspace_members'
    workspace_id = db.Column(db.String(36), db.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),)
