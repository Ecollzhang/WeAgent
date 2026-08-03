"""分支业务逻辑."""
from database import db
from models.branch import RdBranch
from models.requirement import RdRequirement
from models.bug import RdBug
from models.activity import RdActivityLog


class BranchService:

    def list_branches(self, project_id, source_type=None, source_id=None):
        q = RdBranch.query.filter_by(project_id=project_id)
        if source_type:
            q = q.filter_by(source_type=source_type)
        if source_id:
            q = q.filter_by(source_id=source_id)
        return [b.to_dict() for b in q.order_by(RdBranch.created_at.desc()).all()]

    def create_branch(self, project_id, data, user_id=None):
        """创建分支并自动关联到需求或Bug."""
        branch_name = data['branch_name'].strip()
        source_type = data['source_type']
        source_id = data['source_id']

        # 自动生成分支名（如果未提供）
        if not branch_name:
            branch_name = self._generate_branch_name(source_type, source_id)

        # 验证关联对象存在
        if source_type == 'requirement':
            obj = RdRequirement.query.filter_by(id=source_id, project_id=project_id).first()
        else:
            obj = RdBug.query.filter_by(id=source_id, project_id=project_id).first()
        if not obj:
            return None, '关联的需求或Bug不存在'

        branch = RdBranch(
            project_id=project_id,
            repo_id=data.get('repo_id'),
            branch_name=branch_name,
            base_branch=data.get('base_branch', 'main'),
            source_type=source_type,
            source_id=source_id,
            created_by=user_id,
        )
        db.session.add(branch)
        self._log(db.session, project_id, source_type, source_id,
                  'updated', user_id, new_value={'branch_created': branch_name})
        db.session.commit()
        return branch.to_dict(), None

    def update_branch(self, branch_id, data, user_id=None):
        branch = RdBranch.query.filter_by(id=branch_id).first()
        if not branch:
            return None
        if 'status' in data:
            branch.status = data['status']
            if data['status'] == 'merged':
                from datetime import datetime
                branch.merged_at = datetime.utcnow()
        if 'repo_id' in data:
            branch.repo_id = data['repo_id']
        db.session.commit()
        return branch.to_dict()

    def delete_branch(self, branch_id, user_id=None):
        branch = RdBranch.query.filter_by(id=branch_id).first()
        if not branch:
            return False
        db.session.delete(branch)
        db.session.commit()
        return True

    def _generate_branch_name(self, source_type, source_id):
        if source_type == 'requirement':
            obj = RdRequirement.query.filter_by(id=source_id).first()
            prefix = 'feature/REQ'
        else:
            obj = RdBug.query.filter_by(id=source_id).first()
            prefix = 'fix/BUG'

        if not obj:
            return None

        # 取 ID 后6位作为编号
        short_id = source_id.replace('-', '')[-6:].upper()
        # 标题转 slug
        import re
        title = getattr(obj, 'title', '')
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')[:40]

        return f'{prefix}-{short_id}-{slug}' if slug else f'{prefix}-{short_id}'

    def _log(self, sess, project_id, target_type, target_id, action, actor_id,
             old_value=None, new_value=None):
        log = RdActivityLog(
            project_id=project_id, target_type=target_type, target_id=target_id,
            action=action, actor_id=actor_id,
            old_value=old_value, new_value=new_value,
        )
        sess.add(log)


branch_service = BranchService()
