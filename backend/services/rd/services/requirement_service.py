"""需求业务逻辑."""
from database import db
from models.requirement import RdRequirement, RdRequirementAssignee
from models.activity import RdActivityLog
from datetime import datetime


class RequirementService:

    def list_requirements(self, project_id, filters=None):
        q = RdRequirement.query.filter_by(project_id=project_id)
        if filters:
            if filters.get('iteration_id'):
                q = q.filter_by(iteration_id=filters['iteration_id'])
            if filters.get('priority'):
                q = q.filter_by(priority=filters['priority'])
            if filters.get('status'):
                q = q.filter_by(status=filters['status'])
            if filters.get('type'):
                q = q.filter_by(type=filters['type'])
            if filters.get('assignee_id'):
                q = q.join(RdRequirementAssignee).filter(
                    RdRequirementAssignee.user_id == filters['assignee_id']
                )
        return [r.to_dict() for r in q.order_by(RdRequirement.updated_at.desc()).all()]

    def get_requirement(self, requirement_id):
        r = RdRequirement.query.filter_by(id=requirement_id).first()
        return r.to_dict(include_details=True) if r else None

    def create_requirement(self, project_id, data, user_id=None):
        req = RdRequirement(
            project_id=project_id,
            iteration_id=data.get('iteration_id'),
            parent_id=data.get('parent_id'),
            title=data['title'].strip(),
            description=data.get('description', '').strip() or None,
            acceptance_criteria=data.get('acceptance_criteria', '').strip() or None,
            priority=data.get('priority', 'p2'),
            type=data.get('type', 'feature'),
            story_points=data.get('story_points', 0),
            labels=data.get('labels', []),
            developer_id=data.get('developer_id') or None,
            designer_id=data.get('designer_id') or None,
            tester_id=data.get('tester_id') or None,
            start_date=data.get('start_date'),
            due_date=data.get('due_date'),
            created_by=user_id,
        )
        db.session.add(req)
        db.session.flush()  # 确保 req.id 生成
        self._log(db.session, project_id, 'requirement', req.id,
                  'created', user_id, new_value={'title': data['title']})
        db.session.commit()
        return req.to_dict(include_details=True)

    def update_requirement(self, requirement_id, data, user_id=None):
        req = RdRequirement.query.filter_by(id=requirement_id).first()
        if not req:
            return None
        old_status = req.status

        updatable = ('title', 'description', 'acceptance_criteria', 'priority',
                      'status', 'type', 'story_points', 'labels',
                      'developer_id', 'designer_id', 'tester_id',
                      'start_date', 'due_date', 'iteration_id', 'parent_id')
        for field in updatable:
            if field in data:
                val = data[field]
                if isinstance(val, str) and field not in ('description', 'acceptance_criteria'):
                    val = val.strip() or None
                setattr(req, field, val)

        if 'status' in data and data['status'] == 'done' and not req.completed_at:
            req.completed_at = datetime.utcnow()

        if 'status' in data and data['status'] != old_status:
            self._log(db.session, req.project_id, 'requirement', req.id,
                      'status_changed', user_id,
                      old_value={'status': old_status}, new_value={'status': data['status']})
        else:
            self._log(db.session, req.project_id, 'requirement', req.id,
                      'updated', user_id)

        db.session.commit()
        return req.to_dict(include_details=True)

    def delete_requirement(self, requirement_id, user_id=None):
        req = RdRequirement.query.filter_by(id=requirement_id).first()
        if not req:
            return False
        self._log(db.session, req.project_id, 'requirement', req.id,
                  'deleted', user_id)
        db.session.delete(req)
        db.session.commit()
        return True

    # ── 开发者管理 ──

    def add_assignee(self, requirement_id, user_id, role='primary', actor_id=None):
        req = RdRequirement.query.filter_by(id=requirement_id).first()
        if not req:
            return None
        existing = RdRequirementAssignee.query.filter_by(
            requirement_id=requirement_id, user_id=user_id
        ).first()
        if existing:
            existing.role = role
        else:
            a = RdRequirementAssignee(requirement_id=requirement_id,
                                       user_id=user_id, role=role)
            db.session.add(a)
        self._log(db.session, req.project_id, 'requirement', requirement_id,
                  'assigned', actor_id, new_value={'user_id': user_id, 'role': role})
        db.session.commit()
        return req.to_dict(include_details=True)

    def remove_assignee(self, requirement_id, user_id, actor_id=None):
        a = RdRequirementAssignee.query.filter_by(
            requirement_id=requirement_id, user_id=user_id
        ).first()
        if not a:
            return False
        req = RdRequirement.query.filter_by(id=requirement_id).first()
        self._log(db.session, req.project_id, 'requirement', requirement_id,
                  'assigned', actor_id, old_value={'user_id': user_id, 'role': a.role})
        db.session.delete(a)
        db.session.commit()
        return True

    def _log(self, sess, project_id, target_type, target_id, action, actor_id,
             old_value=None, new_value=None):
        log = RdActivityLog(
            project_id=project_id, target_type=target_type, target_id=target_id,
            action=action, actor_id=actor_id,
            old_value=old_value, new_value=new_value,
        )
        sess.add(log)


requirement_service = RequirementService()
