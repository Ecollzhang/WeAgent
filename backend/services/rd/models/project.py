"""研发项目模型."""
import uuid
from database import db


def gen_uuid():
    return str(uuid.uuid4())


class RdProject(db.Model):
    __tablename__ = 'rd_projects'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    workspace_id = db.Column(db.String(36), nullable=False, comment='所属工作空间')
    user_id = db.Column(db.String(36), nullable=False, comment='创建者')
    name = db.Column(db.String(200), nullable=False, comment='项目名称')
    description = db.Column(db.Text, nullable=True, comment='项目描述')
    cover_url = db.Column(db.String(500), nullable=True, comment='封面图URL')
    tech_stack = db.Column(
        db.JSON,
        nullable=False,
        default=dict,
        comment='技术栈 {"frontend":"Vue","backend":"Flask","database":"MySQL"}',
    )
    coding_standards = db.Column(db.Text, nullable=True, comment='编码规范/团队约定')
    status = db.Column(
        db.Enum('active', 'archived', name='project_status'),
        default='active',
    )
    visibility = db.Column(
        db.Enum('private', 'team', 'public', name='project_visibility'),
        default='team',
        comment='可见性',
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # 关系
    files = db.relationship(
        'RdProjectFile', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )
    members = db.relationship(
        'RdProjectMember', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )
    iterations = db.relationship(
        'RdIteration', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )
    requirements = db.relationship(
        'RdRequirement', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )
    bugs = db.relationship(
        'RdBug', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )
    branches = db.relationship(
        'RdBranch', back_populates='project', cascade='all, delete-orphan', lazy='dynamic'
    )

    def to_dict(self, include_files=False):
        total_reqs = self.requirements.count()
        if total_reqs > 0:
            from models.requirement import RdRequirement
            done = self.requirements.filter(RdRequirement.status.in_(['done', 'closed'])).count()
            completion_rate = round(done / total_reqs * 100)
        else:
            completion_rate = 0

        data = {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description or '',
            'cover_url': self.cover_url or '',
            'tech_stack': self.tech_stack or {},
            'coding_standards': self.coding_standards or '',
            'status': self.status,
            'visibility': self.visibility or 'team',
            'file_count': self.files.count(),
            'member_count': self.members.count(),
            'iteration_count': self.iterations.count(),
            'requirement_count': total_reqs,
            'bug_count': self.bugs.count(),
            'completion_rate': completion_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_files:
            data['files'] = [f.to_dict() for f in self.files.order_by('created_at').all()]
        return data


class RdProjectMember(db.Model):
    """项目成员表."""
    __tablename__ = 'rd_project_members'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    user_id = db.Column(db.String(36), nullable=False, comment='用户ID')
    role = db.Column(
        db.Enum('owner', 'admin', 'developer', 'viewer', name='member_role'),
        default='developer',
    )
    joined_at = db.Column(db.DateTime, server_default=db.func.now())

    project = db.relationship('RdProject', back_populates='members')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
        }
