"""Organization rules for the three-level office collaboration model."""
from extensions import db
from models.organization import OfficeDepartment, OfficeGroup, OfficeMember, OfficeNotification


class OrganizationService:
    ROLES = ('member', 'team_lead', 'department_head')

    def member(self, workspace_id, user_id):
        return OfficeMember.query.filter_by(workspace_id=workspace_id, user_id=user_id, active=True).first()

    def is_head(self, workspace_id, user_id):
        member = self.member(workspace_id, user_id)
        return bool(member and member.role == 'department_head')

    def bootstrap(self, workspace_id, user_id, data):
        if OfficeDepartment.query.filter_by(workspace_id=workspace_id).first():
            return None, 'Organization already exists'
        name = (data.get('department_name') or '').strip()
        display_name = (data.get('display_name') or '').strip()
        if not name or not display_name:
            return None, 'department_name and display_name are required'
        department = OfficeDepartment(workspace_id=workspace_id, name=name, head_user_id=user_id)
        member = OfficeMember(workspace_id=workspace_id, user_id=user_id, display_name=display_name, role='department_head')
        db.session.add_all([department, member])
        db.session.commit()
        return self.structure(workspace_id), None

    def structure(self, workspace_id):
        department = OfficeDepartment.query.filter_by(workspace_id=workspace_id).first()
        groups = OfficeGroup.query.filter_by(workspace_id=workspace_id).order_by(OfficeGroup.created_at).all()
        members = OfficeMember.query.filter_by(workspace_id=workspace_id, active=True).order_by(OfficeMember.role.desc(), OfficeMember.display_name).all()
        return {'department': department.to_dict() if department else None,
                'groups': [item.to_dict() for item in groups],
                'members': [item.to_dict() for item in members]}

    def get_structure(self, workspace_id, user_id):
        # Existing personal workspaces remain readable; organization is initialized explicitly.
        return self.structure(workspace_id), None

    def create_group(self, workspace_id, user_id, data):
        if not self.is_head(workspace_id, user_id):
            return None, 'Only the department head can manage groups'
        name = (data.get('name') or '').strip()
        if not name:
            return None, 'name is required'
        group = OfficeGroup(workspace_id=workspace_id, name=name)
        db.session.add(group); db.session.commit()
        return group.to_dict(), None

    def add_member(self, workspace_id, user_id, data):
        if not self.is_head(workspace_id, user_id):
            return None, 'Only the department head can add members'
        target_id = (data.get('user_id') or '').strip()
        display_name = (data.get('display_name') or '').strip()
        role = data.get('role', 'member')
        if not target_id or not display_name or role not in ('member', 'team_lead'):
            return None, 'user_id, display_name and a valid role are required'
        if OfficeMember.query.filter_by(workspace_id=workspace_id, user_id=target_id).first():
            return None, 'This account is already a member'
        group_id = data.get('group_id') or None
        if group_id and not OfficeGroup.query.filter_by(id=group_id, workspace_id=workspace_id).first():
            return None, 'Group not found'
        manager_id = data.get('manager_user_id') or None
        if manager_id and not self.member(workspace_id, manager_id):
            return None, 'Direct manager is not a workspace member'
        if role == 'team_lead':
            manager_id = user_id
        member = OfficeMember(workspace_id=workspace_id, user_id=target_id, display_name=display_name,
                              role=role, group_id=group_id, manager_user_id=manager_id)
        db.session.add(member)
        if role == 'team_lead' and group_id:
            OfficeGroup.query.filter_by(id=group_id, workspace_id=workspace_id).update({'leader_user_id': target_id})
        self.notify(workspace_id, target_id, 'organization', '你已加入智慧办公部门',
                    f'角色：{"直属领导（小组长）" if role == "team_lead" else "普通成员"}', 'member', target_id)
        db.session.commit()
        return member.to_dict(), None

    def update_member(self, workspace_id, user_id, member_id, data):
        if not self.is_head(workspace_id, user_id):
            return None, 'Only the department head can manage members'
        member = OfficeMember.query.filter_by(id=member_id, workspace_id=workspace_id).first()
        if not member or member.role == 'department_head':
            return None, 'Member not found'
        for field in ('display_name', 'group_id', 'manager_user_id'):
            if field in data:
                setattr(member, field, data[field] or None)
        if data.get('role') in ('member', 'team_lead'):
            member.role = data['role']
            if member.role == 'team_lead': member.manager_user_id = user_id
        db.session.commit()
        return member.to_dict(), None

    def notify(self, workspace_id, recipient_id, notification_type, title, content='', source_type='', source_id=''):
        if not recipient_id:
            return None
        notification = OfficeNotification(workspace_id=workspace_id, recipient_id=recipient_id,
            notification_type=notification_type, title=title, content=content, source_type=source_type, source_id=source_id)
        db.session.add(notification)
        return notification

    def notifications(self, workspace_id, user_id):
        items = OfficeNotification.query.filter_by(workspace_id=workspace_id, recipient_id=user_id).order_by(OfficeNotification.created_at.desc()).limit(100).all()
        return {'items': [item.to_dict() for item in items], 'unread_count': sum(not item.is_read for item in items)}, None

    def read_notification(self, notification_id, user_id):
        item = OfficeNotification.query.filter_by(id=notification_id, recipient_id=user_id).first()
        if not item: return None, 'Notification not found'
        item.is_read = True; db.session.commit()
        return item.to_dict(), None


organization_service = OrganizationService()
