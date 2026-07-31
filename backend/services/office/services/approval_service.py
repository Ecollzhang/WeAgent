"""Approval workflow business logic."""
from datetime import datetime

from extensions import db
from models.approval import Approval
from models.official_document import OfficialDocument
from services.helpers import page_args
from services.organization_service import organization_service


class ApprovalService:
    """Manage lightweight serial approvals."""

    def list(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        if not workspace_id:
            return None, 'workspace_id is required'
        page, page_size = page_args(params)
        query = Approval.query.filter_by(workspace_id=workspace_id)
        if params.get('status'):
            query = query.filter_by(status=params['status'])
        pagination = query.order_by(Approval.updated_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        items = []
        for item in pagination.items:
            if item.initiator_id != user_id and user_id not in [step.get('approver_id') for step in (item.steps or [])]:
                continue
            data = item.to_dict()
            data['can_handle'] = item.status == 'pending' and self._current_approver(item) == user_id
            items.append(data)
        return {'items': items, 'total': pagination.total, 'page': page, 'page_size': page_size}, None

    def get(self, approval_id, user_id):
        """Return the approval flow together with its associated document."""
        approval = Approval.query.filter_by(id=approval_id).first()
        if not approval:
            return None, 'Approval not found'
        if approval.initiator_id != user_id and self._current_approver(approval) != user_id:
            return None, 'No permission to view this approval'
        result = approval.to_dict()
        document = OfficialDocument.query.get(approval.document_id) if approval.document_id else None
        result['document'] = document.to_dict() if document else None
        result['can_handle'] = approval.status == 'pending' and self._current_approver(approval) == user_id
        return result, None

    @staticmethod
    def _current_approver(approval):
        for step in approval.steps or []:
            if step.get('step') == approval.current_step:
                return step.get('approver_id')
        return None

    def _get_pending(self, approval_id):
        approval = Approval.query.filter_by(id=approval_id).first()
        if not approval:
            return None, 'Approval not found'
        if approval.status != 'pending':
            return None, 'Approval is no longer pending'
        return approval, None

    def approve(self, approval_id, user_id, comment=''):
        approval, error = self._get_pending(approval_id)
        if error:
            return None, error
        if self._current_approver(approval) != user_id:
            return None, 'You are not the current approver'
        steps = list(approval.steps or [])
        history = list(approval.history or [])
        for step in steps:
            if step.get('step') == approval.current_step:
                step['status'] = 'approved'
                step['comment'] = comment
                step['handled_at'] = datetime.utcnow().isoformat(timespec='seconds')
                break
        history.append({'step': approval.current_step, 'action': 'approved', 'user_id': user_id, 'comment': comment})
        if approval.current_step >= len(steps):
            approval.status = 'approved'
            document = OfficialDocument.query.get(approval.document_id)
            if document:
                document.status = 'approved'
                document.reviewer_id = user_id
                document.review_comment = comment
            organization_service.notify(approval.workspace_id, approval.initiator_id, 'approval_result',
                f'审批通过：{approval.title}', '公文已完成全部审批，可发布。', 'approval', approval.id)
        else:
            approval.current_step += 1
            next_user = self._current_approver(approval)
            organization_service.notify(approval.workspace_id, next_user, 'approval',
                f'待审批：{approval.title}', '上一审批节点已通过，请继续处理。', 'approval', approval.id)
        approval.steps = steps
        approval.history = history
        db.session.commit()
        return approval.to_dict(), None

    def reject(self, approval_id, user_id, comment):
        approval, error = self._get_pending(approval_id)
        if error:
            return None, error
        if self._current_approver(approval) != user_id:
            return None, 'You are not the current approver'
        if not (comment or '').strip():
            return None, 'A rejection comment is required'
        approval.status = 'rejected'
        approval.history = list(approval.history or []) + [{
            'step': approval.current_step, 'action': 'rejected', 'user_id': user_id, 'comment': comment,
        }]
        document = OfficialDocument.query.get(approval.document_id)
        if document:
            document.status = 'draft'
            document.reviewer_id = user_id
            document.review_comment = comment
        organization_service.notify(approval.workspace_id, approval.initiator_id, 'approval_result',
            f'审批驳回：{approval.title}', comment, 'approval', approval.id)
        db.session.commit()
        return approval.to_dict(), None

    def withdraw(self, approval_id, user_id):
        approval, error = self._get_pending(approval_id)
        if error:
            return None, error
        if approval.initiator_id != user_id:
            return None, 'Only the initiator can withdraw this approval'
        approval.status = 'cancelled'
        approval.history = list(approval.history or []) + [{
            'step': approval.current_step, 'action': 'withdrawn', 'user_id': user_id,
        }]
        document = OfficialDocument.query.get(approval.document_id)
        if document:
            document.status = 'draft'
        db.session.commit()
        return approval.to_dict(), None


approval_service = ApprovalService()
