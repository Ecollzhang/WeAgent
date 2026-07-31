"""Office dashboard aggregation."""
from datetime import datetime, timedelta

from models.action_item import ActionItem
from models.approval import Approval
from models.meeting import Meeting
from models.official_document import OfficialDocument


class DashboardService:
    """Build lightweight workspace-scoped office statistics."""

    def summary(self, user_id, workspace_id):
        if not workspace_id:
            return None, 'workspace_id is required'
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        actions = ActionItem.query.filter_by(workspace_id=workspace_id, creator_id=user_id)
        total_actions = actions.count()
        completed_actions = actions.filter_by(status='done').count()
        overdue_actions = actions.filter(
            ActionItem.status.notin_(['done', 'cancelled']),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < now,
        ).count()
        documents = OfficialDocument.query.filter_by(workspace_id=workspace_id, user_id=user_id)
        document_statuses = {
            status: documents.filter_by(status=status).count()
            for status in ('draft', 'reviewing', 'approved', 'published', 'archived')
        }
        return {
            'pending_approvals': Approval.query.filter_by(
                workspace_id=workspace_id, status='pending'
            ).count(),
            'meetings_this_week': Meeting.query.filter(
                Meeting.workspace_id == workspace_id,
                Meeting.organizer_id == user_id,
                Meeting.start_time >= week_start,
            ).count(),
            'action_items': {
                'total': total_actions,
                'completed': completed_actions,
                'overdue': overdue_actions,
                'completion_rate': round(completed_actions / total_actions * 100, 1) if total_actions else 0,
            },
            'documents_by_status': document_statuses,
        }, None


dashboard_service = DashboardService()
