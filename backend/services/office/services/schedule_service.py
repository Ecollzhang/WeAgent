"""Schedule and conflict-detection business logic."""
from models.schedule import Schedule
from extensions import db
from services.helpers import page_args, parse_datetime


class ScheduleService:
    """Manage user schedules within an office workspace."""
    VALID_TYPES = ('meeting', 'task', 'reminder', 'other')
    VALID_STATUSES = ('pending', 'done', 'cancelled')

    def list(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        if not workspace_id:
            return None, 'workspace_id is required'
        page, page_size = page_args(params)
        query = Schedule.query.filter_by(workspace_id=workspace_id, user_id=user_id)
        pagination = query.order_by(Schedule.start_time).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
        }, None

    def _conflicts(self, user_id, workspace_id, start_time, end_time, exclude_id=None):
        query = Schedule.query.filter(
            Schedule.user_id == user_id,
            Schedule.workspace_id == workspace_id,
            Schedule.status != 'cancelled',
            Schedule.start_time < end_time,
            Schedule.end_time > start_time,
        )
        if exclude_id:
            query = query.filter(Schedule.id != exclude_id)
        return [item.to_dict() for item in query.order_by(Schedule.start_time).all()]

    def create(self, user_id, data):
        try:
            workspace_id = (data.get('workspace_id') or '').strip()
            title = (data.get('title') or '').strip()
            if not workspace_id:
                return None, 'workspace_id is required'
            if not title:
                return None, 'title is required'
            start_time = parse_datetime(data.get('start_time'), 'start_time', required=True)
            end_time = parse_datetime(data.get('end_time'), 'end_time', required=True)
            if end_time < start_time:
                return None, 'end_time must not be earlier than start_time'
        except ValueError as error:
            return None, str(error)
        event_type = data.get('event_type', 'task')
        if event_type not in self.VALID_TYPES:
            return None, 'Invalid event_type'
        schedule = Schedule(
            workspace_id=workspace_id, user_id=user_id, title=title,
            description=data.get('description', ''), event_type=event_type,
            start_time=start_time, end_time=end_time,
            priority=data.get('priority', 'medium'),
            meeting_id=data.get('meeting_id'), action_item_id=data.get('action_item_id'),
        )
        conflicts = self._conflicts(user_id, workspace_id, start_time, end_time)
        db.session.add(schedule)
        db.session.commit()
        result = schedule.to_dict()
        result['conflicts'] = conflicts
        return result, None

    def update(self, schedule_id, user_id, data):
        schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            return None, 'Schedule not found'
        try:
            if 'start_time' in data:
                schedule.start_time = parse_datetime(data.get('start_time'), 'start_time', required=True)
            if 'end_time' in data:
                schedule.end_time = parse_datetime(data.get('end_time'), 'end_time', required=True)
        except ValueError as error:
            return None, str(error)
        if schedule.end_time < schedule.start_time:
            return None, 'end_time must not be earlier than start_time'
        for field in ('title', 'description', 'priority', 'meeting_id', 'action_item_id'):
            if field in data:
                setattr(schedule, field, data[field])
        if 'event_type' in data:
            if data['event_type'] not in self.VALID_TYPES:
                return None, 'Invalid event_type'
            schedule.event_type = data['event_type']
        if 'status' in data:
            if data['status'] not in self.VALID_STATUSES:
                return None, 'Invalid status'
            schedule.status = data['status']
        conflicts = self._conflicts(user_id, schedule.workspace_id, schedule.start_time, schedule.end_time, schedule.id)
        db.session.commit()
        result = schedule.to_dict()
        result['conflicts'] = conflicts
        return result, None

    def conflicts(self, user_id, data):
        try:
            workspace_id = (data.get('workspace_id') or '').strip()
            if not workspace_id:
                return None, 'workspace_id is required'
            start_time = parse_datetime(data.get('start_time'), 'start_time', required=True)
            end_time = parse_datetime(data.get('end_time'), 'end_time', required=True)
        except ValueError as error:
            return None, str(error)
        return self._conflicts(user_id, workspace_id, start_time, end_time, data.get('exclude_id')), None


schedule_service = ScheduleService()
