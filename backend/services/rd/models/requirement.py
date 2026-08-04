"""需求模型."""
from database import db
from models.project import gen_uuid


class RdRequirement(db.Model):
    __tablename__ = 'rd_requirements'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    iteration_id = db.Column(
        db.String(36), db.ForeignKey('rd_iterations.id', ondelete='SET NULL'), nullable=True
    )
    parent_id = db.Column(
        db.String(36), db.ForeignKey('rd_requirements.id', ondelete='SET NULL'),
        nullable=True, comment='父需求ID, 支持子需求拆分'
    )
    title = db.Column(db.String(300), nullable=False, comment='需求标题')
    description = db.Column(db.Text, nullable=True, comment='需求描述(Markdown)')
    acceptance_criteria = db.Column(db.Text, nullable=True, comment='验收标准(Markdown)')
    priority = db.Column(
        db.Enum('p0', 'p1', 'p2', 'p3', name='req_priority'),
        default='p2',
    )
    status = db.Column(
        db.Enum('backlog', 'todo', 'in_progress', 'in_review', 'done', 'closed',
                name='req_status'),
        default='backlog',
    )
    type = db.Column(
        db.Enum('feature', 'enhancement', 'bugfix', 'tech_debt', 'research',
                name='req_type'),
        default='feature',
        comment='需求类型',
    )
    story_points = db.Column(db.Integer, default=0, comment='故事点(0-100)')
    labels = db.Column(db.JSON, nullable=True, comment='标签数组')
    developer_id = db.Column(db.String(36), nullable=True, comment='开发人员ID')
    designer_id = db.Column(db.String(36), nullable=True, comment='设计人员ID')
    tester_id = db.Column(db.String(36), nullable=True, comment='测试人员ID')
    start_date = db.Column(db.Date, nullable=True, comment='计划开始日期')
    due_date = db.Column(db.Date, nullable=True, comment='计划截止日期')
    completed_at = db.Column(db.DateTime, nullable=True, comment='实际完成时间')
    created_by = db.Column(db.String(36), nullable=True, comment='创建者ID')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # 关系
    project = db.relationship('RdProject', back_populates='requirements')
    iteration = db.relationship('RdIteration', back_populates='requirements')
    assignees = db.relationship(
        'RdRequirementAssignee', back_populates='requirement',
        cascade='all, delete-orphan', lazy='joined'
    )
    children = db.relationship(
        'RdRequirement', backref=db.backref('parent', remote_side=[id]),
        lazy='joined'
    )
    comments = db.relationship(
        'RdComment',
        primaryjoin="and_(RdRequirement.id==RdComment.target_id, "
                     "RdComment.target_type=='requirement')",
        foreign_keys='RdComment.target_id',
        cascade='all, delete-orphan', lazy='dynamic',
        order_by='RdComment.created_at.asc()'
    )
    bugs = db.relationship(
        'RdBug',
        secondary='rd_bug_requirements',
        lazy='dynamic',
        back_populates='requirements'
    )

    def to_dict(self, include_details=False):
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'iteration_id': self.iteration_id,
            'iteration_name': self.iteration.name if self.iteration else None,
            'parent_id': self.parent_id,
            'title': self.title,
            'description': self.description or '',
            'acceptance_criteria': self.acceptance_criteria or '',
            'priority': self.priority,
            'status': self.status,
            'type': self.type,
            'story_points': self.story_points,
            'labels': self.labels or [],
            'developer_id': self.developer_id or '',
            'designer_id': self.designer_id or '',
            'tester_id': self.tester_id or '',
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assignees': [a.to_dict() for a in self.assignees],
        }
        if include_details:
            data['children'] = [c.to_dict() for c in self.children]
            data['comments_count'] = self.comments.count()
            data['branches'] = self._get_branches()
        return data

    def _get_branches(self):
        from models.branch import RdBranch
        branches = RdBranch.query.filter_by(
            source_type='requirement', source_id=self.id
        ).all()
        return [b.to_dict() for b in branches]


class RdRequirementAssignee(db.Model):
    """需求-开发者关联表."""
    __tablename__ = 'rd_requirement_assignees'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    requirement_id = db.Column(
        db.String(36), db.ForeignKey('rd_requirements.id', ondelete='CASCADE'), nullable=False
    )
    user_id = db.Column(db.String(36), nullable=False, comment='用户ID')
    role = db.Column(
        db.Enum('primary', 'reviewer', 'tester', name='assignee_role'),
        default='primary',
    )
    assigned_at = db.Column(db.DateTime, server_default=db.func.now())

    requirement = db.relationship('RdRequirement', back_populates='assignees')

    def to_dict(self):
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'user_id': self.user_id,
            'role': self.role,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
        }
