"""Meeting and action-item business logic."""
from datetime import timedelta
from models.action_item import ActionItem
from models.meeting import Meeting
from models.schedule import Schedule
from extensions import db
from services.helpers import page_args, parse_datetime
from services.organization_service import organization_service


class MeetingService:
    """Manage workspace-scoped meetings and their follow-up actions."""
    VALID_STATUSES = ('scheduled', 'ongoing', 'completed', 'cancelled')
    VALID_ACTION_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')

    def list(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        if not workspace_id:
            return None, 'workspace_id is required'
        page, page_size = page_args(params)
        query = Meeting.query.filter_by(workspace_id=workspace_id)
        status = params.get('status')
        if status:
            query = query.filter_by(status=status)
        pagination = query.order_by(Meeting.start_time.desc(), Meeting.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        visible = [item for item in pagination.items if item.organizer_id == user_id or user_id in self._participant_ids(item)]
        return {
            'items': [item.to_dict() for item in visible],
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
        }, None

    def get(self, meeting_id, user_id):
        meeting = Meeting.query.get(meeting_id)
        if not meeting or (meeting.organizer_id != user_id and user_id not in self._participant_ids(meeting)):
            return None, 'Meeting not found'
        result = meeting.to_dict()
        result['action_items'] = [item.to_dict() for item in meeting.action_items.order_by(ActionItem.due_date).all()]
        return result, None

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
            if end_time <= start_time:
                return None, 'end_time must be later than start_time'
        except ValueError as error:
            return None, str(error)

        meeting = Meeting(
            workspace_id=workspace_id,
            organizer_id=user_id,
            title=title,
            agenda=data.get('agenda', ''),
            participants=data.get('participants') or [],
            location=data.get('location', ''),
            meeting_link=data.get('meeting_link', ''),
            start_time=start_time,
            end_time=end_time,
            transcript=data.get('transcript', ''),
            materials=data.get('materials') or [],
            status=data.get('status', 'scheduled'),
        )
        if meeting.status not in self.VALID_STATUSES:
            return None, 'Invalid meeting status'
        db.session.add(meeting)
        db.session.flush()
        db.session.add(Schedule(
            workspace_id=workspace_id, user_id=user_id, title=title,
            description=data.get('agenda', ''), event_type='meeting',
            start_time=start_time, end_time=end_time, meeting_id=meeting.id,
        ))
        db.session.add(Schedule(
            workspace_id=workspace_id, user_id=user_id,
            title=f'会后维护：{title}', description='[meeting_followup]请完善会议纪要、记录与行动项',
            event_type='task', start_time=end_time, end_time=end_time + timedelta(hours=1),
            priority='high', meeting_id=meeting.id,
        ))
        for participant_id in self._participant_ids(meeting):
            if participant_id == user_id:
                continue
            db.session.add(Schedule(workspace_id=workspace_id, user_id=participant_id, title=title,
                description=data.get('agenda', ''), event_type='meeting', start_time=start_time,
                end_time=end_time, meeting_id=meeting.id))
            organization_service.notify(workspace_id, participant_id, 'meeting_invitation',
                f'会议邀请：{title}', f'{start_time:%Y-%m-%d %H:%M}，地点：{meeting.location or "待定"}', 'meeting', meeting.id)
        db.session.commit()
        return meeting.to_dict(), None

    @staticmethod
    def _sync_followup_task(meeting):
        followup = Schedule.query.filter(
            Schedule.meeting_id == meeting.id,
            Schedule.user_id == meeting.organizer_id,
            Schedule.event_type == 'task',
            Schedule.description.like('[meeting_followup]%'),
        ).first()
        if not followup:
            return
        has_minutes = bool((meeting.minutes or '').strip())
        has_actions = ActionItem.query.filter_by(meeting_id=meeting.id).count() > 0
        followup.status = 'done' if has_minutes and has_actions else 'pending'

    def update(self, meeting_id, user_id, data):
        meeting = Meeting.query.filter_by(id=meeting_id, organizer_id=user_id).first()
        if not meeting:
            return None, 'Meeting not found'
        try:
            if 'start_time' in data:
                meeting.start_time = parse_datetime(data.get('start_time'), 'start_time', required=True)
            if 'end_time' in data:
                meeting.end_time = parse_datetime(data.get('end_time'), 'end_time', required=True)
        except ValueError as error:
            return None, str(error)
        if meeting.end_time <= meeting.start_time:
            return None, 'end_time must be later than start_time'
        for field in ('title', 'agenda', 'participants', 'location', 'meeting_link', 'transcript', 'minutes', 'materials', 'resolutions'):
            if field in data:
                setattr(meeting, field, data[field])
        if 'status' in data:
            if data['status'] not in self.VALID_STATUSES:
                return None, 'Invalid meeting status'
            meeting.status = data['status']
        self._sync_followup_task(meeting)
        schedule = Schedule.query.filter_by(
            meeting_id=meeting.id, user_id=user_id, event_type='meeting'
        ).first()
        if schedule:
            schedule.title = meeting.title
            schedule.description = meeting.agenda or ''
            schedule.start_time = meeting.start_time
            schedule.end_time = meeting.end_time
            if meeting.status == 'cancelled':
                schedule.status = 'cancelled'
        db.session.commit()
        return meeting.to_dict(), None

    def delete(self, meeting_id, user_id):
        """Delete a meeting and the schedules generated from its action items."""
        meeting = Meeting.query.filter_by(id=meeting_id, organizer_id=user_id).first()
        if not meeting:
            return None, 'Meeting not found'
        Schedule.query.filter_by(meeting_id=meeting.id).delete(synchronize_session=False)
        db.session.delete(meeting)
        db.session.commit()
        return {'id': meeting_id}, None

    def create_action_item(self, meeting_id, user_id, data):
        meeting = Meeting.query.filter_by(id=meeting_id, organizer_id=user_id).first()
        if not meeting:
            return None, 'Meeting not found'
        title = (data.get('title') or '').strip()
        if not title:
            return None, 'title is required'
        try:
            due_date = parse_datetime(data.get('due_date'), 'due_date')
        except ValueError as error:
            return None, str(error)
        action_item = ActionItem(
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            creator_id=user_id,
            assignee_id=(data.get('assignee_id') or user_id).strip(),
            assignee_name=data.get('assignee_name', ''),
            title=title,
            description=data.get('description', ''),
            due_date=due_date,
            priority=data.get('priority', 'medium'),
        )
        db.session.add(action_item)
        db.session.flush()
        if data.get('create_schedule', True) and due_date:
            schedule = Schedule(
                workspace_id=meeting.workspace_id,
                user_id=action_item.assignee_id,
                title=title,
                description=data.get('description', ''),
                event_type='task',
                start_time=due_date,
                # A task needs a non-zero interval for calendar conflict checks.
                end_time=due_date + timedelta(hours=1),
                priority=action_item.priority,
                action_item_id=action_item.id,
                meeting_id=meeting.id,
            )
            db.session.add(schedule)
            db.session.flush()
            action_item.schedule_id = schedule.id
        if action_item.assignee_id and action_item.assignee_id != user_id:
            organization_service.notify(meeting.workspace_id, action_item.assignee_id, 'action_item',
                f'新的行动项：{title}', f'截止时间：{due_date.strftime("%Y-%m-%d %H:%M") if due_date else "未设置"}', 'action_item', action_item.id)
        self._sync_followup_task(meeting)
        db.session.commit()
        return action_item.to_dict(), None

    @staticmethod
    def _participant_ids(meeting):
        return [item.get('user_id') for item in (meeting.participants or []) if isinstance(item, dict) and item.get('user_id')]

    def update_action_item(self, action_item_id, user_id, data):
        action_item = ActionItem.query.filter_by(id=action_item_id, creator_id=user_id).first()
        if not action_item:
            return None, 'Action item not found'
        for field in ('title', 'description', 'assignee_id', 'assignee_name', 'priority'):
            if field in data:
                setattr(action_item, field, data[field])
        if 'status' in data:
            if data['status'] not in self.VALID_ACTION_STATUSES:
                return None, 'Invalid action item status'
            action_item.status = data['status']
            if action_item.schedule_id:
                schedule = Schedule.query.get(action_item.schedule_id)
                if schedule:
                    schedule.status = 'done' if action_item.status == 'done' else 'pending'
        if 'due_date' in data:
            try:
                action_item.due_date = parse_datetime(data.get('due_date'), 'due_date')
            except ValueError as error:
                return None, str(error)
        db.session.commit()
        return action_item.to_dict(), None


meeting_service = MeetingService()
