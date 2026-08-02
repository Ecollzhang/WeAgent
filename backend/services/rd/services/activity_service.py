"""活动日志业务逻辑."""
from database import db
from models.activity import RdActivityLog


class ActivityService:

    def list_activities(self, project_id, target_type=None, target_id=None,
                        page=1, per_page=20):
        q = RdActivityLog.query.filter_by(project_id=project_id)
        if target_type:
            q = q.filter_by(target_type=target_type)
        if target_id:
            q = q.filter_by(target_id=target_id)
        total = q.count()
        items = q.order_by(RdActivityLog.created_at.desc()) \
                 .offset((page - 1) * per_page).limit(per_page).all()
        return {
            'items': [a.to_dict() for a in items],
            'total': total,
            'page': page,
            'per_page': per_page,
        }


activity_service = ActivityService()
