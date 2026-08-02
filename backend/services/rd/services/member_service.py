"""项目成员业务逻辑."""
from database import db
from models.project import RdProjectMember


class MemberService:

    def list_members(self, project_id):
        members = RdProjectMember.query.filter_by(project_id=project_id).all()
        return [m.to_dict() for m in members]

    def add_member(self, project_id, user_id, role='developer'):
        existing = RdProjectMember.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()
        if existing:
            existing.role = role
        else:
            m = RdProjectMember(project_id=project_id, user_id=user_id, role=role)
            db.session.add(m)
        db.session.commit()
        return existing.to_dict() if existing else m.to_dict()

    def update_member_role(self, project_id, user_id, role):
        m = RdProjectMember.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()
        if not m:
            return None
        m.role = role
        db.session.commit()
        return m.to_dict()

    def remove_member(self, project_id, user_id):
        m = RdProjectMember.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()
        if not m:
            return False
        db.session.delete(m)
        db.session.commit()
        return True


member_service = MemberService()
