"""迭代业务逻辑."""
from database import db
from models.iteration import RdIteration
from models.activity import RdActivityLog
from datetime import datetime


class IterationService:

    def list_iterations(self, project_id, user_id=None):
        from sqlalchemy import case
        q = RdIteration.query.filter_by(project_id=project_id)
        # active 排最前，其次按 sort_order
        q = q.order_by(
            case((RdIteration.status == 'active', 0), else_=1),
            RdIteration.sort_order.asc()
        )
        return [i.to_dict() for i in q.all()]

    def get_iteration(self, iteration_id):
        i = RdIteration.query.filter_by(id=iteration_id).first()
        return i.to_dict() if i else None

    def create_iteration(self, project_id, data, user_id=None):
        iteration = RdIteration(
            project_id=project_id,
            name=data['name'].strip(),
            goal=data.get('goal', '').strip() or None,
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            sort_order=data.get('sort_order', 0),
        )
        db.session.add(iteration)
        db.session.flush()  # ensure iteration.id is populated before _log
        self._log(db.session, project_id, 'iteration', iteration.id,
                  'created', user_id, new_value={'name': data['name']})
        db.session.commit()
        return iteration.to_dict()

    def update_iteration(self, iteration_id, data, user_id=None):
        iteration = RdIteration.query.filter_by(id=iteration_id).first()
        if not iteration:
            return None
        old_status = iteration.status

        for field in ('name', 'goal', 'start_date', 'end_date', 'sort_order',
                       'progress_manual'):
            if field in data:
                val = data[field]
                if isinstance(val, str):
                    val = val.strip() or None
                setattr(iteration, field, val)
        if 'status' in data:
            iteration.status = data['status']

        changes = {}
        if 'status' in data and data['status'] != old_status:
            changes['status'] = {'from': old_status, 'to': data['status']}
        if changes:
            self._log(db.session, iteration.project_id, 'iteration', iteration.id,
                      'status_changed', user_id, old_value={'status': old_status},
                      new_value={'status': iteration.status})

        db.session.commit()
        return iteration.to_dict()

    def delete_iteration(self, iteration_id, user_id=None):
        iteration = RdIteration.query.filter_by(id=iteration_id).first()
        if not iteration:
            return False
        self._log(db.session, iteration.project_id, 'iteration', iteration.id,
                  'deleted', user_id)
        db.session.delete(iteration)
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


iteration_service = IterationService()
