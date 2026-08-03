"""构建管理模型 — CI/CD 构建记录与步骤."""
from database import db
from models.project import gen_uuid


class RdBuild(db.Model):
    __tablename__ = 'rd_builds'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    build_number = db.Column(db.Integer, nullable=False, comment='构建编号')
    build_type = db.Column(
        db.String(20), nullable=False, default='push',
        comment='触发方式：push / manual / schedule / mr'
    )
    status = db.Column(
        db.Enum('pending', 'running', 'success', 'failed', 'cancelled', name='build_status'),
        default='pending',
    )
    commit_hash = db.Column(db.String(40), nullable=True, comment='Git 提交哈希')
    commit_message = db.Column(db.String(500), nullable=True, comment='提交信息')
    branch = db.Column(db.String(200), nullable=True, comment='分支名')
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True, comment='构建耗时（秒）')
    created_by = db.Column(db.String(36), nullable=True, comment='触发者')
    repo_id = db.Column(db.String(36), db.ForeignKey('rd_repos.id', ondelete='SET NULL'), nullable=True, comment='关联仓库ID')
    workflow_id = db.Column(db.String(100), nullable=True, comment='GitHub Actions workflow ID')
    github_run_id = db.Column(db.BigInteger, nullable=True, comment='GitHub Actions run ID')
    error_summary = db.Column(db.Text, nullable=True, comment='失败摘要')
    preview_url = db.Column(db.String(500), nullable=True, comment='预览部署链接')
    artifacts = db.Column(db.JSON, nullable=True, comment='构建产物列表 ["dist/xxx.zip"]')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    steps = db.relationship('RdBuildStep', back_populates='build',
                            cascade='all, delete-orphan', lazy='joined',
                            order_by='RdBuildStep.step_order')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'build_number': self.build_number,
            'build_type': self.build_type,
            'status': self.status,
            'commit_hash': self.commit_hash,
            'commit_message': self.commit_message,
            'branch': self.branch,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_seconds': self.duration_seconds,
            'created_by': self.created_by,
            'repo_id': self.repo_id,
            'workflow_id': self.workflow_id,
            'github_run_id': self.github_run_id,
            'error_summary': self.error_summary,
            'preview_url': self.preview_url,
            'artifacts': self.artifacts or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'steps': [s.to_dict() for s in (self.steps or [])],
        }


class RdBuildStep(db.Model):
    __tablename__ = 'rd_build_steps'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    build_id = db.Column(
        db.String(36), db.ForeignKey('rd_builds.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    step_name = db.Column(db.String(100), nullable=False, comment='步骤名称')
    step_order = db.Column(db.Integer, nullable=False, comment='执行顺序')
    status = db.Column(
        db.Enum('pending', 'running', 'success', 'failed', 'skipped', name='step_status'),
        default='pending',
    )
    command = db.Column(db.String(500), nullable=True, comment='执行命令')
    duration_seconds = db.Column(db.Integer, nullable=True, comment='耗时（秒）')
    log = db.Column(db.Text, nullable=True, comment='步骤日志输出')

    build = db.relationship('RdBuild', back_populates='steps')

    def to_dict(self):
        return {
            'id': self.id,
            'build_id': self.build_id,
            'step_name': self.step_name,
            'step_order': self.step_order,
            'status': self.status,
            'command': self.command,
            'duration_seconds': self.duration_seconds,
            'log': self.log,
        }
