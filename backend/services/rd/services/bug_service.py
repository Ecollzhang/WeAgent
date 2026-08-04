"""Bug 业务逻辑."""
from database import db
from models.bug import RdBug, RdBugAssignee
from models.requirement import RdRequirement
from models.activity import RdActivityLog
from datetime import datetime


class BugService:

    def list_bugs(self, project_id, filters=None):
        q = RdBug.query.filter_by(project_id=project_id)
        if filters:
            if filters.get('iteration_id'):
                q = q.filter_by(iteration_id=filters['iteration_id'])
            if filters.get('severity'):
                q = q.filter_by(severity=filters['severity'])
            if filters.get('priority'):
                q = q.filter_by(priority=filters['priority'])
            if filters.get('status'):
                q = q.filter_by(status=filters['status'])
            if filters.get('assignee_id'):
                q = q.join(RdBugAssignee).filter(
                    RdBugAssignee.user_id == filters['assignee_id']
                )
        return [b.to_dict() for b in q.order_by(RdBug.updated_at.desc()).all()]

    def get_bug(self, bug_id):
        b = RdBug.query.filter_by(id=bug_id).first()
        return b.to_dict(include_details=True) if b else None

    def _sync_requirement_ids(self, bug, requirement_ids, user_id=None):
        """同步多对多关联需求."""
        from models.bug import rd_bug_requirements
        if requirement_ids is None:
            return
        # 清除旧关联
        db.session.execute(
            rd_bug_requirements.delete().where(
                rd_bug_requirements.c.bug_id == bug.id
            )
        )
        # 添加新关联
        if requirement_ids:
            reqs = RdRequirement.query.filter(
                RdRequirement.id.in_(requirement_ids)
            ).all()
            bug.requirements = reqs
            # 同时设置 requirement_id 为第一个（向后兼容）
            bug.requirement_id = requirement_ids[0] if requirement_ids else None

    def create_bug(self, project_id, data, user_id=None):
        requirement_ids = data.get('requirement_ids')
        bug = RdBug(
            project_id=project_id,
            iteration_id=data.get('iteration_id'),
            requirement_id=data.get('requirement_id') or (requirement_ids[0] if requirement_ids else None),
            title=data['title'].strip(),
            description=data.get('description', '').strip() or None,
            expected_behavior=data.get('expected_behavior', '').strip() or None,
            actual_behavior=data.get('actual_behavior', '').strip() or None,
            severity=data.get('severity', 'major'),
            priority=data.get('priority', 'p2'),
            environment=data.get('environment', '').strip() or None,
            browser_info=data.get('browser_info', '').strip() or None,
            os_info=data.get('os_info', '').strip() or None,
            attachments=data.get('attachments', []),
            labels=data.get('labels', []),
            developer_id=data.get('developer_id') or None,
            designer_id=data.get('designer_id') or None,
            tester_id=data.get('tester_id') or None,
            created_by=user_id,
        )
        db.session.add(bug)
        db.session.flush()  # 确保 bug.id 生成

        # 同步关联需求
        if requirement_ids:
            reqs = RdRequirement.query.filter(
                RdRequirement.id.in_(requirement_ids)
            ).all()
            bug.requirements = reqs

        self._log(db.session, project_id, 'bug', bug.id,
                  'created', user_id, new_value={'title': data['title']})
        db.session.commit()
        return bug.to_dict(include_details=True)

    def update_bug(self, bug_id, data, user_id=None):
        bug = RdBug.query.filter_by(id=bug_id).first()
        if not bug:
            return None
        old_status = bug.status

        updatable = ('title', 'description', 'expected_behavior', 'actual_behavior',
                      'severity', 'priority', 'status', 'environment',
                      'browser_info', 'os_info', 'attachments', 'labels',
                      'developer_id', 'designer_id', 'tester_id',
                      'iteration_id', 'requirement_id')
        for field in updatable:
            if field in data:
                val = data[field]
                if isinstance(val, str) and field not in ('description', 'expected_behavior',
                                                           'actual_behavior'):
                    val = val.strip() or None
                setattr(bug, field, val)

        # 处理 requirement_ids 数组（多对多关联）
        if 'requirement_ids' in data:
            self._sync_requirement_ids(bug, data['requirement_ids'], user_id)

        if 'status' in data:
            if data['status'] == 'fixed' and not bug.fixed_at:
                bug.fixed_at = datetime.utcnow()
            elif data['status'] == 'verified' and not bug.verified_at:
                bug.verified_at = datetime.utcnow()

        if 'status' in data and data['status'] != old_status:
            self._log(db.session, bug.project_id, 'bug', bug.id,
                      'status_changed', user_id,
                      old_value={'status': old_status}, new_value={'status': data['status']})
        else:
            self._log(db.session, bug.project_id, 'bug', bug.id,
                      'updated', user_id)

        db.session.commit()
        return bug.to_dict(include_details=True)

    def delete_bug(self, bug_id, user_id=None):
        bug = RdBug.query.filter_by(id=bug_id).first()
        if not bug:
            return False
        self._log(db.session, bug.project_id, 'bug', bug.id,
                  'deleted', user_id)
        db.session.delete(bug)
        db.session.commit()
        return True

    # ── 修复人管理 ──

    def add_assignee(self, bug_id, user_id, role='fixer', actor_id=None):
        bug = RdBug.query.filter_by(id=bug_id).first()
        if not bug:
            return None
        existing = RdBugAssignee.query.filter_by(
            bug_id=bug_id, user_id=user_id
        ).first()
        if existing:
            existing.role = role
        else:
            a = RdBugAssignee(bug_id=bug_id, user_id=user_id, role=role)
            db.session.add(a)
        self._log(db.session, bug.project_id, 'bug', bug_id,
                  'assigned', actor_id, new_value={'user_id': user_id, 'role': role})
        db.session.commit()
        return bug.to_dict(include_details=True)

    def remove_assignee(self, bug_id, user_id, actor_id=None):
        a = RdBugAssignee.query.filter_by(bug_id=bug_id, user_id=user_id).first()
        if not a:
            return False
        bug = RdBug.query.filter_by(id=bug_id).first()
        self._log(db.session, bug.project_id, 'bug', bug_id,
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


bug_service = BugService()
