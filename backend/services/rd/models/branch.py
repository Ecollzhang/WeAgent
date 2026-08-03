"""分支模型 — 需求/Bug 关联的代码分支."""
from database import db
from models.project import gen_uuid


class RdBranch(db.Model):
    __tablename__ = 'rd_branches'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    repo_id = db.Column(db.String(36), nullable=True, comment='关联仓库ID')
    branch_name = db.Column(db.String(200), nullable=False, comment='分支名')
    base_branch = db.Column(db.String(200), default='main', comment='基于哪个分支创建')
    source_type = db.Column(
        db.Enum('requirement', 'bug', name='branch_source_type'),
        nullable=False,
    )
    source_id = db.Column(db.String(36), nullable=False, comment='需求ID或BugID')
    status = db.Column(
        db.Enum('active', 'merged', 'closed', name='branch_status'),
        default='active',
    )
    created_by = db.Column(db.String(36), nullable=True, comment='创建者')
    merged_at = db.Column(db.DateTime, nullable=True, comment='合入时间')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    project = db.relationship('RdProject', back_populates='branches')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'repo_id': self.repo_id,
            'branch_name': self.branch_name,
            'base_branch': self.base_branch,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'status': self.status,
            'created_by': self.created_by,
            'merged_at': self.merged_at.isoformat() if self.merged_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
