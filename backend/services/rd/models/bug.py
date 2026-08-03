"""Bug 模型."""
from database import db
from models.project import gen_uuid

# Bug-需求多对多关联表
rd_bug_requirements = db.Table(
    'rd_bug_requirements',
    db.Column('bug_id', db.String(36), db.ForeignKey('rd_bugs.id', ondelete='CASCADE'), primary_key=True),
    db.Column('requirement_id', db.String(36), db.ForeignKey('rd_requirements.id', ondelete='CASCADE'), primary_key=True),
)


class RdBug(db.Model):
    __tablename__ = 'rd_bugs'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    iteration_id = db.Column(
        db.String(36), db.ForeignKey('rd_iterations.id', ondelete='SET NULL'), nullable=True
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey('rd_requirements.id', ondelete='SET NULL'),
        nullable=True, comment='关联需求(单数,向后兼容)'
    )
    title = db.Column(db.String(300), nullable=False, comment='Bug标题')
    description = db.Column(db.Text, nullable=True, comment='复现步骤')
    expected_behavior = db.Column(db.Text, nullable=True, comment='期望行为')
    actual_behavior = db.Column(db.Text, nullable=True, comment='实际行为')
    severity = db.Column(
        db.Enum('blocker', 'critical', 'major', 'minor', 'trivial', name='bug_severity'),
        default='major',
    )
    priority = db.Column(
        db.Enum('p0', 'p1', 'p2', 'p3', name='bug_priority'),
        default='p2',
    )
    status = db.Column(
        db.Enum('open', 'confirmed', 'in_progress', 'fixed', 'verified', 'closed',
                'wont_fix', name='bug_status'),
        default='open',
    )
    environment = db.Column(db.String(200), nullable=True, comment='运行环境')
    browser_info = db.Column(db.String(200), nullable=True, comment='浏览器信息')
    os_info = db.Column(db.String(200), nullable=True, comment='操作系统信息')
    developer_id = db.Column(db.String(36), nullable=True, comment='开发人员ID')
    designer_id = db.Column(db.String(36), nullable=True, comment='设计人员ID')
    tester_id = db.Column(db.String(36), nullable=True, comment='测试人员ID')
    attachments = db.Column(db.JSON, nullable=True, comment='附件URL数组')
    labels = db.Column(db.JSON, nullable=True, comment='标签数组')
    created_by = db.Column(db.String(36), nullable=True, comment='提交者ID')
    fixed_at = db.Column(db.DateTime, nullable=True, comment='修复时间')
    verified_at = db.Column(db.DateTime, nullable=True, comment='验证时间')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # 关系
    project = db.relationship('RdProject', back_populates='bugs')
    iteration = db.relationship('RdIteration', back_populates='bugs')
    assignees = db.relationship(
        'RdBugAssignee', back_populates='bug',
        cascade='all, delete-orphan', lazy='joined'
    )
    comments = db.relationship(
        'RdComment',
        primaryjoin="and_(RdBug.id==RdComment.target_id, "
                     "RdComment.target_type=='bug')",
        foreign_keys='RdComment.target_id',
        cascade='all, delete-orphan', lazy='dynamic',
        order_by='RdComment.created_at.asc()'
    )
    requirements = db.relationship(
        'RdRequirement',
        secondary=rd_bug_requirements,
        lazy='joined',
        back_populates='bugs'
    )

    def to_dict(self, include_details=False):
        requirement_ids = [r.id for r in self.requirements] if self.requirements else []
        # 向后兼容：如果关联表有数据用关联表，否则回退到 requirement_id 单值
        if not requirement_ids and self.requirement_id:
            requirement_ids = [self.requirement_id]

        data = {
            'id': self.id,
            'project_id': self.project_id,
            'iteration_id': self.iteration_id,
            'iteration_name': self.iteration.name if self.iteration else None,
            'requirement_id': self.requirement_id,
            'requirement_ids': requirement_ids,
            'title': self.title,
            'description': self.description or '',
            'expected_behavior': self.expected_behavior or '',
            'actual_behavior': self.actual_behavior or '',
            'severity': self.severity,
            'priority': self.priority,
            'status': self.status,
            'environment': self.environment or '',
            'browser_info': self.browser_info or '',
            'os_info': self.os_info or '',
            'developer_id': self.developer_id or '',
            'designer_id': self.designer_id or '',
            'tester_id': self.tester_id or '',
            'attachments': self.attachments or [],
            'labels': self.labels or [],
            'created_by': self.created_by,
            'fixed_at': self.fixed_at.isoformat() if self.fixed_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assignees': [a.to_dict() for a in self.assignees],
        }
        if include_details:
            data['comments_count'] = self.comments.count()
            data['branches'] = self._get_branches()
        return data

    def _get_branches(self):
        from models.branch import RdBranch
        branches = RdBranch.query.filter_by(
            source_type='bug', source_id=self.id
        ).all()
        return [b.to_dict() for b in branches]


class RdBugAssignee(db.Model):
    """Bug-开发者关联表."""
    __tablename__ = 'rd_bug_assignees'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    bug_id = db.Column(
        db.String(36), db.ForeignKey('rd_bugs.id', ondelete='CASCADE'), nullable=False
    )
    user_id = db.Column(db.String(36), nullable=False, comment='用户ID')
    role = db.Column(
        db.Enum('fixer', 'reviewer', 'tester', name='bug_assignee_role'),
        default='fixer',
    )
    assigned_at = db.Column(db.DateTime, server_default=db.func.now())

    bug = db.relationship('RdBug', back_populates='assignees')

    def to_dict(self):
        return {
            'id': self.id,
            'bug_id': self.bug_id,
            'user_id': self.user_id,
            'role': self.role,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
        }
