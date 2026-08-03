"""代码审查模型 — AI 驱动的多维度代码审查."""
from database import db
from models.project import gen_uuid


class RdReview(db.Model):
    __tablename__ = 'rd_reviews'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    repo_id = db.Column(db.String(36), nullable=True, comment='关联仓库ID（粘贴代码时可空）')
    title = db.Column(db.String(200), nullable=False, comment='审查标题')
    description = db.Column(db.Text, nullable=True, comment='审查说明')
    code_content = db.Column(db.Text, nullable=False, comment='被审查的代码内容')
    file_paths = db.Column(db.JSON, nullable=True, comment='文件路径列表')
    language = db.Column(db.String(50), nullable=True, comment='编程语言')
    branch = db.Column(db.String(200), nullable=True, comment='来源分支')
    commit_sha = db.Column(db.String(40), nullable=True, comment='来源提交 SHA')
    review_method = db.Column(
        db.String(20), nullable=False, default='script',
        comment='审查方式：script（脚本审查）、llm（AI 审查）'
    )
    status = db.Column(
        db.Enum('pending', 'reviewing', 'completed', 'failed', name='review_status'),
        default='pending',
    )
    summary = db.Column(db.Text, nullable=True, comment='审查总结')
    overall_score = db.Column(db.Float, nullable=True, comment='综合评分 0-10')
    scores = db.Column(db.JSON, nullable=True, comment='各维度评分 {security,style,logic,performance}')
    agent_conversation_id = db.Column(db.String(36), nullable=True, comment='关联 agent 会话')
    created_by = db.Column(db.String(36), nullable=True, comment='创建者')
    reviewed_at = db.Column(db.DateTime, nullable=True, comment='审查完成时间')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    issues = db.relationship('RdReviewIssue', back_populates='review',
                             cascade='all, delete-orphan', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'repo_id': self.repo_id,
            'title': self.title,
            'description': self.description,
            'code_content': self.code_content,
            'file_paths': self.file_paths or [],
            'language': self.language,
            'branch': self.branch,
            'commit_sha': self.commit_sha,
            'status': self.status,
            'review_method': self.review_method,
            'summary': self.summary,
            'overall_score': self.overall_score,
            'scores': self.scores or {},
            'agent_conversation_id': self.agent_conversation_id,
            'created_by': self.created_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'issues': [i.to_dict() for i in (self.issues or [])],
        }


class RdReviewIssue(db.Model):
    __tablename__ = 'rd_review_issues'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    review_id = db.Column(
        db.String(36), db.ForeignKey('rd_reviews.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    severity = db.Column(
        db.Enum('critical', 'warning', 'suggestion', name='issue_severity'),
        nullable=False,
    )
    category = db.Column(
        db.Enum('security', 'style', 'logic', 'performance', name='issue_category'),
        nullable=False,
    )
    file_path = db.Column(db.String(500), nullable=True, comment='问题所在文件')
    line_start = db.Column(db.Integer, nullable=True, comment='起始行号')
    line_end = db.Column(db.Integer, nullable=True, comment='结束行号')
    title = db.Column(db.String(300), nullable=False, comment='问题标题')
    description = db.Column(db.Text, nullable=True, comment='问题详细描述')
    suggestion = db.Column(db.Text, nullable=True, comment='修复建议')
    code_snippet = db.Column(db.Text, nullable=True, comment='问题代码片段')
    fixed_snippet = db.Column(db.Text, nullable=True, comment='修复后代码片段')
    status = db.Column(
        db.Enum('open', 'fixed', 'ignored', name='issue_status'),
        default='open',
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    review = db.relationship('RdReview', back_populates='issues')

    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'severity': self.severity,
            'category': self.category,
            'file_path': self.file_path,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'title': self.title,
            'description': self.description,
            'suggestion': self.suggestion,
            'code_snippet': self.code_snippet,
            'fixed_snippet': self.fixed_snippet,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
