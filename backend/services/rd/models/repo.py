"""代码仓库模型 — GitHub OAuth Config + Token + 关联仓库."""
from database import db
from models.project import gen_uuid


class RdGithubOAuthConfig(db.Model):
    """GitHub OAuth App 配置 — 由用户通过前端设置，不依赖 .env."""
    __tablename__ = 'rd_github_oauth_config'

    id = db.Column(db.String(36), primary_key=True, default=lambda: 'default')
    client_id = db.Column(db.String(200), nullable=False)
    client_secret = db.Column(db.Text, nullable=False, comment='加密存储')
    redirect_uri = db.Column(db.String(500), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class RdGithubToken(db.Model):
    """GitHub OAuth Token — 加密存储."""
    __tablename__ = 'rd_github_tokens'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), index=True, nullable=False, comment='平台用户ID')
    github_user = db.Column(db.String(100), nullable=False, comment='GitHub 用户名')
    access_token = db.Column(db.Text, nullable=False, comment='加密存储的 access token')
    token_type = db.Column(db.String(50), default='bearer')
    scopes = db.Column(db.String(500), comment='授权的权限范围')
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'github_user': self.github_user,
            'scopes': self.scopes.split(',') if self.scopes else [],
            'token_type': self.token_type,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RdRepo(db.Model):
    """关联的 GitHub 仓库（元数据），不存储代码."""
    __tablename__ = 'rd_repos'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'),
        index=True, nullable=False
    )
    github_id = db.Column(db.BigInteger, nullable=False, comment='GitHub repo ID')
    owner = db.Column(db.String(200), nullable=False, comment='仓库拥有者 (user/org)')
    repo_name = db.Column(db.String(200), nullable=False, comment='仓库名')
    full_name = db.Column(db.String(400), nullable=False, comment='owner/repo')
    description = db.Column(db.Text, nullable=True)
    default_branch = db.Column(db.String(100), default='main')
    language = db.Column(db.String(50), nullable=True)
    html_url = db.Column(db.String(500), comment='GitHub 页面链接')
    clone_url = db.Column(db.String(500), nullable=True)
    private = db.Column(db.Boolean, default=False)
    status = db.Column(
        db.Enum('active', 'archived', name='repo_status'),
        default='active'
    )
    synced_at = db.Column(db.DateTime, nullable=True, comment='最后同步时间')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    project = db.relationship('RdProject', backref='repos')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'github_id': self.github_id,
            'owner': self.owner,
            'repo_name': self.repo_name,
            'full_name': self.full_name,
            'description': self.description,
            'default_branch': self.default_branch,
            'language': self.language,
            'html_url': self.html_url,
            'clone_url': self.clone_url,
            'private': self.private,
            'status': self.status,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
