"""迭代模型."""
from database import db
from models.project import gen_uuid


class RdIteration(db.Model):
    __tablename__ = 'rd_iterations'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    name = db.Column(db.String(200), nullable=False, comment='迭代名称')
    goal = db.Column(db.Text, nullable=True, comment='迭代目标')
    start_date = db.Column(db.Date, nullable=True, comment='开始日期')
    end_date = db.Column(db.Date, nullable=True, comment='结束日期')
    status = db.Column(
        db.Enum('planning', 'active', 'completed', 'cancelled', name='iteration_status'),
        default='planning',
    )
    sort_order = db.Column(db.Integer, default=0, comment='排序序号')
    progress_manual = db.Column(db.Integer, nullable=True, comment='手动设置的进度(0-100)')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    project = db.relationship('RdProject', back_populates='iterations')
    requirements = db.relationship(
        'RdRequirement', back_populates='iteration', lazy='dynamic'
    )
    bugs = db.relationship(
        'RdBug', back_populates='iteration', lazy='dynamic'
    )

    def get_progress(self):
        """自动计算迭代进度."""
        from models.requirement import RdRequirement
        from models.bug import RdBug

        reqs = self.requirements.filter(
            ~RdRequirement.status.in_(['backlog', 'closed'])
        ).all()
        bugs = self.bugs.filter(
            ~RdBug.status.in_(['open', 'closed', 'wont_fix'])
        ).all()
        all_items = list(reqs) + list(bugs)
        if not all_items:
            return 0
        done_statuses = {'done', 'closed', 'fixed', 'verified'}
        done = sum(1 for i in all_items if i.status in done_statuses)
        return round(done / len(all_items) * 100)

    def to_dict(self):
        auto_progress = self.get_progress()
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'goal': self.goal or '',
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'sort_order': self.sort_order,
            'progress': self.progress_manual if self.progress_manual is not None else auto_progress,
            'progress_auto': auto_progress,
            'progress_manual': self.progress_manual,
            'requirement_count': self.requirements.count(),
            'bug_count': self.bugs.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        return data
