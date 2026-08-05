"""Workspace organization, membership and in-app notification models."""
from extensions import db
from models.base import OfficeBaseModel


class OfficeDepartment(OfficeBaseModel):
    __tablename__ = 'office_departments'
    workspace_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    head_user_id = db.Column(db.String(36), nullable=False, index=True)


class OfficeGroup(OfficeBaseModel):
    __tablename__ = 'office_groups'
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    leader_user_id = db.Column(db.String(36), nullable=True, index=True)


class OfficeMember(OfficeBaseModel):
    __tablename__ = 'office_members'
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('member', 'team_lead', 'department_head', name='office_member_role'), nullable=False, default='member')
    group_id = db.Column(db.String(36), nullable=True, index=True)
    manager_user_id = db.Column(db.String(36), nullable=True, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint('workspace_id', 'user_id', name='uq_office_member_workspace_user'),)


class OfficeNotification(OfficeBaseModel):
    __tablename__ = 'office_notifications'
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    recipient_id = db.Column(db.String(36), nullable=False, index=True)
    notification_type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    source_type = db.Column(db.String(30), default='')
    source_id = db.Column(db.String(36), default='', index=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
