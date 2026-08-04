"""活动日志模型."""
from database import db
from models.project import gen_uuid


class RdActivityLog(db.Model):
    __tablename__ = 'rd_activity_logs'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    target_type = db.Column(
        db.Enum('requirement', 'bug', 'iteration', 'project', 'review', 'branch',
                name='activity_target_type'),
        nullable=False,
    )
    target_id = db.Column(db.String(36), nullable=False, comment='目标ID')
    action = db.Column(
        db.Enum('created', 'updated', 'status_changed', 'assigned', 'commented', 'deleted',
                name='activity_action'),
        nullable=False,
    )
    actor_id = db.Column(db.String(36), nullable=True, comment='操作者ID')
    old_value = db.Column(db.JSON, nullable=True, comment='变更前值')
    new_value = db.Column(db.JSON, nullable=True, comment='变更后值')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'action': self.action,
            'actor_id': self.actor_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
