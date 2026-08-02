"""仓库关联业务逻辑."""
from database import db
from models.repo import RdRepo, RdGithubToken
from services.github_service import encrypt_token, decrypt_token


class RepoService:

    # ── Token 管理 ─────────────────────────────────────────

    def save_token(self, user_id, token_data):
        """保存或更新 GitHub OAuth Token（加密存储）."""
        github_user = token_data.get('github_user', '')
        existing = RdGithubToken.query.filter_by(user_id=user_id).first()
        if existing:
            existing.access_token = encrypt_token(token_data['access_token'])
            existing.github_user = github_user
            existing.token_type = token_data.get('token_type', 'bearer')
            existing.scopes = token_data.get('scope', '')
            existing.expires_at = None
        else:
            t = RdGithubToken(
                user_id=user_id,
                github_user=github_user,
                access_token=encrypt_token(token_data['access_token']),
                token_type=token_data.get('token_type', 'bearer'),
                scopes=token_data.get('scope', ''),
            )
            db.session.add(t)
        db.session.commit()

    def get_token(self, user_id):
        """获取用户解密后的 token."""
        t = RdGithubToken.query.filter_by(user_id=user_id).first()
        if not t:
            return None
        return decrypt_token(t.access_token)

    def get_token_status(self, user_id):
        """检查授权状态."""
        t = RdGithubToken.query.filter_by(user_id=user_id).first()
        if not t:
            return {'connected': False}
        return {
            'connected': True,
            'github_user': t.github_user,
            'scopes': t.scopes.split(',') if t.scopes else [],
            'created_at': t.created_at.isoformat() if t.created_at else None,
        }

    def revoke_token(self, user_id):
        """撤销授权."""
        t = RdGithubToken.query.filter_by(user_id=user_id).first()
        if t:
            db.session.delete(t)
            db.session.commit()
            return True
        return False

    # ── 仓库 CRUD ──────────────────────────────────────────

    def list_repos(self, project_id):
        repos = RdRepo.query.filter_by(
            project_id=project_id, status='active'
        ).order_by(RdRepo.created_at.desc()).all()
        return [r.to_dict() for r in repos]

    def list_all_repos_for_user(self, user_id, project_id=None):
        """获取用户有权限的所有项目的仓库，可按项目过滤."""
        from models.project import RdProjectMember
        # 查出用户参与的所有项目ID
        member_query = RdProjectMember.query.filter_by(user_id=user_id)
        if project_id:
            member_query = member_query.filter_by(project_id=project_id)
        project_ids = [m.project_id for m in member_query.all()]
        if not project_ids:
            return []
        # 查出这些项目下的活跃仓库
        query = RdRepo.query.filter(
            RdRepo.project_id.in_(project_ids),
            RdRepo.status == 'active'
        ).order_by(RdRepo.created_at.desc())
        repos = query.all()
        return [r.to_dict() for r in repos]

    def get_repo(self, repo_id):
        r = RdRepo.query.filter_by(id=repo_id).first()
        return r.to_dict() if r else None

    def create_repo(self, project_id, data):
        """关联 GitHub 仓库到项目."""
        full_name = data['full_name']
        owner, repo_name = full_name.split('/', 1)
        existing = RdRepo.query.filter_by(
            project_id=project_id, full_name=full_name
        ).first()
        if existing:
            # 重新激活并更新字段（描述、语言等可能已变化）
            existing.status = 'active'
            existing.description = data.get('description', '')
            existing.default_branch = data.get('default_branch', 'main')
            existing.language = data.get('language', '')
            existing.html_url = data.get('html_url', '')
            existing.clone_url = data.get('clone_url', '')
            existing.private = data.get('private', False)
            db.session.commit()
            return existing.to_dict()

        repo = RdRepo(
            project_id=project_id,
            github_id=data.get('github_id', 0),
            owner=owner,
            repo_name=repo_name,
            full_name=full_name,
            description=data.get('description', ''),
            default_branch=data.get('default_branch', 'main'),
            language=data.get('language', ''),
            html_url=data.get('html_url', ''),
            clone_url=data.get('clone_url', ''),
            private=data.get('private', False),
        )
        db.session.add(repo)
        db.session.commit()
        return repo.to_dict()

    def delete_repo(self, repo_id):
        """取消关联（软删除 → 归档）."""
        r = RdRepo.query.filter_by(id=repo_id).first()
        if not r:
            return False
        r.status = 'archived'
        db.session.commit()
        return True


repo_service = RepoService()
