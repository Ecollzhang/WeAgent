"""Workspace business logic — 工作空间服务."""
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.conversation import Conversation
from app import db


class WorkspaceService:
    """工作空间 CRUD 服务."""

    VALID_DOMAINS = ('rd', 'edu', 'office')

    # ── CRUD ──────────────────────────────────────────────────────────

    def create(self, user_id, data):
        """创建工作空间."""
        domain = (data.get('domain') or '').strip()
        name = (data.get('name') or '').strip()

        if domain not in self.VALID_DOMAINS:
            return None, f'Invalid domain: {domain}. Must be one of {self.VALID_DOMAINS}'
        if not name:
            return None, 'Workspace name is required'
        if len(name) > 200:
            return None, 'Workspace name is too long (max 200 characters)'

        existing = Workspace.query.filter_by(
            user_id=user_id, domain=domain, name=name
        ).first()
        if existing:
            return None, f'Workspace "{name}" already exists in this domain'

        sub_role = (data.get('sub_role') or '').strip()
        if sub_role and domain == 'edu' and sub_role not in ('teacher', 'student'):
            return None, 'sub_role must be teacher or student for edu domain'

        ws = Workspace(
            user_id=user_id,
            domain=domain,
            sub_role=sub_role,
            name=name,
            description=data.get('description', ''),
            icon=data.get('icon', 'default'),
        )
        ws.save()
        return ws.to_dict(), None

    def list_by_user(self, user_id, domain=None):
        """获取用户的工作空间列表，可按领域过滤."""
        q = Workspace.query.filter(
            Workspace.status == 'active',
            (Workspace.user_id == user_id) | Workspace.id.in_(
                db.session.query(WorkspaceMember.workspace_id).filter_by(user_id=user_id)
            )
        )
        if domain:
            q = q.filter_by(domain=domain)
        workspaces = q.order_by(Workspace.sort_order, Workspace.created_at).all()
        return [w.to_dict() for w in workspaces], None

    def get_by_id(self, workspace_id, user_id):
        """获取单个工作空间详情（含会话数量）."""
        ws = Workspace.query.filter_by(id=workspace_id).first()
        if ws and ws.user_id != user_id and not WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first():
            ws = None
        if not ws:
            return None, 'Workspace not found'
        return ws.to_dict(), None

    def update(self, workspace_id, user_id, data):
        """更新工作空间."""
        ws = Workspace.query.filter_by(id=workspace_id, user_id=user_id).first()
        if not ws:
            return None, 'Workspace not found'

        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return None, 'Workspace name cannot be empty'
            if len(name) > 200:
                return None, 'Workspace name is too long'
            ws.name = name
        if 'description' in data:
            ws.description = data['description']
        if 'icon' in data:
            ws.icon = data['icon']
        if 'sub_role' in data:
            sub_role = (data['sub_role'] or '').strip()
            if sub_role and ws.domain == 'edu' and sub_role not in ('teacher', 'student'):
                return None, 'sub_role must be teacher or student for edu domain'
            ws.sub_role = sub_role
        if 'sort_order' in data:
            ws.sort_order = data['sort_order']

        db.session.commit()
        return ws.to_dict(), None

    def archive(self, workspace_id, user_id):
        """归档工作空间（软删除）."""
        ws = Workspace.query.filter_by(id=workspace_id, user_id=user_id).first()
        if not ws:
            return None, 'Workspace not found'
        ws.status = 'archived'
        db.session.commit()
        return {'archived': True}, None

    def add_member(self, workspace_id, owner_id, member_user_id):
        workspace = Workspace.query.filter_by(id=workspace_id, user_id=owner_id, status='active').first()
        if not workspace:
            return None, 'Only the workspace owner can add members'
        if member_user_id == owner_id:
            return {'workspace_id': workspace_id, 'user_id': member_user_id}, None
        item = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=member_user_id).first()
        if not item:
            item = WorkspaceMember(workspace_id=workspace_id, user_id=member_user_id)
            db.session.add(item); db.session.commit()
        return item.to_dict(), None

    # ── 查询辅助 ──────────────────────────────────────────────────────

    def get_domains(self):
        """返回所有可用领域列表."""
        return [
            {'key': 'rd', 'name': '智能研发', 'icon': 'el-icon-monitor'},
            {'key': 'edu', 'name': '智慧教育', 'icon': 'el-icon-reading'},
            {'key': 'office', 'name': '智慧办公', 'icon': 'el-icon-s-home'},
        ], None


workspace_service = WorkspaceService()
