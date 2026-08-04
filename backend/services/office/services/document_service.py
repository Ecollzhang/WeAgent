"""Official document and template business logic."""
from datetime import datetime

from extensions import db
from models.approval import Approval
from models.document_template import DocumentTemplate
from models.document_receipt import DocumentReceipt
from models.meeting import Meeting
from models.official_document import OfficialDocument
from services.helpers import page_args
from services.organization_service import organization_service


class DocumentService:
    """Manage office documents, templates and submission for approval."""
    VALID_TYPES = ('notice', 'report', 'request', 'letter', 'minutes', 'other')

    @staticmethod
    def _recipient_ids(document):
        return [item.get('user_id') for item in (document.recipients or []) if isinstance(item, dict) and item.get('user_id')]

    @staticmethod
    def _normalise_recipients(workspace_id, recipients):
        """Only organization members can receive an office document."""
        result, seen = [], set()
        for item in recipients:
            user_id = item.get('user_id') if isinstance(item, dict) else item
            if not user_id or user_id in seen:
                continue
            member = organization_service.member(workspace_id, user_id)
            if not member:
                continue
            seen.add(user_id)
            result.append({'user_id': user_id, 'display_name': member.display_name})
        return result

    @staticmethod
    def _normalise_approvers(workspace_id, approvers):
        """Only team leads and department heads can approve office documents."""
        result, seen = [], set()
        for item in approvers:
            user_id = item.get('user_id') if isinstance(item, dict) else item
            if not user_id or user_id in seen:
                continue
            member = organization_service.member(workspace_id, user_id)
            if not member or member.role not in ('team_lead', 'department_head'):
                continue
            seen.add(user_id)
            result.append({'user_id': user_id, 'display_name': member.display_name})
        return result

    @staticmethod
    def _approver_ids(document):
        return [item.get('user_id') for item in (document.approvers or []) if isinstance(item, dict) and item.get('user_id')]

    @staticmethod
    def _recipient_summary(document, receipts=None):
        recipients = document.recipients or []
        names = [item.get('display_name') or item.get('name') or '成员' for item in recipients if isinstance(item, dict)]
        confirmed = sum(1 for item in (receipts or []) if item.confirmed_at)
        return {'names': names, 'total': len(names), 'confirmed': confirmed}

    @staticmethod
    def _reviewer_name(document):
        if not document.reviewer_id:
            return ''
        member = organization_service.member(document.workspace_id, document.reviewer_id)
        return member.display_name if member else ''

    def list_documents(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        error = organization_service.require_access(workspace_id, user_id)
        if error:
            return None, error
        page, page_size = page_args(params)
        query = OfficialDocument.query.filter_by(workspace_id=workspace_id)
        if params.get('status'):
            query = query.filter_by(status=params['status'])
        visible = []
        for item in query.order_by(OfficialDocument.updated_at.desc()).all():
            is_approver = any(user_id == step.get('approver_id') for approval in Approval.query.filter_by(document_id=item.id).all() for step in (approval.steps or []))
            can_receive = user_id in self._recipient_ids(item)
            if item.user_id == user_id or is_approver or can_receive:
                visible.append(item)
        total = len(visible)
        visible = visible[(page - 1) * page_size: page * page_size]
        items = []
        for item in visible:
            data = item.to_dict()
            receipts = DocumentReceipt.query.filter_by(document_id=item.id).all() if item.status == 'published' else []
            data['recipient_summary'] = self._recipient_summary(item, receipts)
            data['reviewer_name'] = self._reviewer_name(item)
            my_receipt = None
            if item.status == 'published' and user_id in self._recipient_ids(item):
                my_receipt = DocumentReceipt.query.filter_by(document_id=item.id, recipient_id=user_id).first()
            data['my_receipt'] = my_receipt.to_dict() if my_receipt else None
            items.append(data)
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        }, None

    def get_document(self, document_id, user_id):
        document = OfficialDocument.query.get(document_id)
        if document and not organization_service.can_access(document.workspace_id, user_id):
            document = None
        if document and document.user_id != user_id:
            related = Approval.query.filter_by(document_id=document.id).all()
            is_approver = any(user_id == step.get('approver_id') for item in related for step in (item.steps or []))
            if not is_approver and user_id not in self._recipient_ids(document):
                document = None
        if not document:
            return None, 'Document not found'
        result = document.to_dict()
        receipts = DocumentReceipt.query.filter_by(document_id=document.id).order_by(DocumentReceipt.created_at).all()
        result['receipts'] = [item.to_dict() for item in receipts]
        result['recipient_summary'] = self._recipient_summary(document, receipts)
        result['reviewer_name'] = self._reviewer_name(document)
        result['approvals'] = [
            item.to_dict()
            for item in Approval.query.filter_by(document_id=document.id).order_by(Approval.created_at.desc()).all()
        ]
        return result, None

    def create_document(self, user_id, data):
        workspace_id = (data.get('workspace_id') or '').strip()
        title = (data.get('title') or '').strip()
        document_type = data.get('document_type', 'notice')
        error = organization_service.require_access(workspace_id, user_id)
        if error:
            return None, error
        if not title:
            return None, 'title is required'
        if document_type not in self.VALID_TYPES:
            return None, 'Invalid document_type'
        template_id = data.get('template_id')
        content = data.get('content', '')
        if template_id and not content:
            template = DocumentTemplate.query.filter(
                DocumentTemplate.id == template_id,
                (DocumentTemplate.workspace_id == workspace_id) | (DocumentTemplate.is_system.is_(True)),
            ).first()
            if not template:
                return None, 'Document template not found'
            content = template.content
        recipients = self._normalise_recipients(workspace_id, data.get('recipients') or [])
        approvers = self._normalise_approvers(workspace_id, data.get('approvers') or [])
        document = OfficialDocument(
            workspace_id=workspace_id, user_id=user_id, meeting_id=data.get('meeting_id'),
            title=title, document_type=document_type, content=content,
            recipients=recipients, approvers=approvers, template_id=template_id,
        )
        db.session.add(document)
        db.session.commit()
        return document.to_dict(), None

    def create_from_meeting(self, meeting_id, user_id, data):
        meeting = Meeting.query.filter_by(id=meeting_id, organizer_id=user_id).first()
        if not meeting:
            return None, 'Meeting not found'
        return self.create_document(user_id, {
            'workspace_id': meeting.workspace_id,
            'meeting_id': meeting.id,
            'title': data.get('title') or f'{meeting.title}会议通知',
            'document_type': data.get('document_type', 'notice'),
            'template_id': data.get('template_id'),
            'content': data.get('content') or (
                f'# {meeting.title}\n\n根据会议决议，现将相关事项通知如下：\n\n{meeting.minutes or meeting.agenda}'
            ),
        })

    def update_document(self, document_id, user_id, data):
        document = OfficialDocument.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return None, 'Document not found'
        if document.status in ('published', 'archived'):
            return None, 'Published or archived documents cannot be edited'
        for field in ('title', 'content', 'template_id', 'meeting_id', 'recipients', 'approvers'):
            if field in data:
                setattr(document, field, self._normalise_recipients(document.workspace_id, data[field] or []) if field == 'recipients' else self._normalise_approvers(document.workspace_id, data[field] or []) if field == 'approvers' else data[field])
        if 'document_type' in data:
            if data['document_type'] not in self.VALID_TYPES:
                return None, 'Invalid document_type'
            document.document_type = data['document_type']
        db.session.commit()
        return document.to_dict(), None

    def list_templates(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        error = organization_service.require_access(workspace_id, user_id)
        if error:
            return None, error
        query = DocumentTemplate.query.filter(
            (DocumentTemplate.workspace_id == workspace_id) | (DocumentTemplate.is_system.is_(True))
        )
        if params.get('document_type'):
            query = query.filter_by(document_type=params['document_type'])
        return [item.to_dict() for item in query.order_by(DocumentTemplate.is_system.desc()).all()], None

    def create_template(self, user_id, data):
        workspace_id = (data.get('workspace_id') or '').strip()
        name = (data.get('name') or '').strip()
        document_type = data.get('document_type', 'notice')
        if not workspace_id or not name or not data.get('content'):
            return None, 'workspace_id, name and content are required'
        error = organization_service.require_access(workspace_id, user_id)
        if error:
            return None, error
        if document_type not in self.VALID_TYPES:
            return None, 'Invalid document_type'
        template = DocumentTemplate(
            workspace_id=workspace_id, creator_id=user_id, name=name,
            document_type=document_type, content=data['content'],
            format_spec=data.get('format_spec', ''),
        )
        db.session.add(template)
        db.session.commit()
        return template.to_dict(), None

    def update_template(self, template_id, user_id, data):
        template = DocumentTemplate.query.filter_by(id=template_id, creator_id=user_id).first()
        if not template or template.is_system:
            return None, 'Template not found or cannot be edited'
        for field in ('name', 'content', 'format_spec'):
            if field in data and data[field] is not None:
                setattr(template, field, data[field])
        if data.get('document_type') in self.VALID_TYPES:
            template.document_type = data['document_type']
        db.session.commit()
        return template.to_dict(), None

    def delete_template(self, template_id, user_id):
        template = DocumentTemplate.query.filter_by(id=template_id, creator_id=user_id).first()
        if not template or template.is_system:
            return None, 'Template not found or cannot be deleted'
        db.session.delete(template); db.session.commit()
        return {'id': template_id}, None

    def submit(self, document_id, user_id, data):
        document = OfficialDocument.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return None, 'Document not found'
        if document.status != 'draft':
            return None, 'Only draft documents can be submitted'
        member = organization_service.member(document.workspace_id, user_id)
        if member and member.role == 'department_head':
            document.status = 'approved'
            document.reviewer_id = user_id
            db.session.commit()
            return {'document_id': document.id, 'status': 'approved', 'steps': []}, None
        steps = data.get('steps') or []
        if not steps:
            if document.approvers:
                # 按角色分层：直属领导（team_lead）为第一级并行审批，部门负责人（department_head）为第二级
                leads, heads, others = [], [], []
                for item in document.approvers:
                    approver_member = organization_service.member(document.workspace_id, item['user_id'])
                    role = approver_member.role if approver_member else ''
                    if role == 'department_head':
                        heads.append(item)
                    elif role == 'team_lead':
                        leads.append(item)
                    else:
                        others.append(item)
                first_stage = others + leads
                second_stage_no = 2 if first_stage else 1
                steps = [{'step': 1, 'approver_id': item['user_id'], 'status': 'pending'} for item in first_stage]
                steps += [{'step': second_stage_no, 'approver_id': item['user_id'], 'status': 'pending'} for item in heads]
            elif not member or not member.manager_user_id:
                return None, '请先在组织架构中设置直属领导后再提交审批'
            else:
                steps = [{'step': 1, 'approver_id': member.manager_user_id, 'status': 'pending'}]
                department = __import__('models.organization', fromlist=['OfficeDepartment']).OfficeDepartment.query.filter_by(workspace_id=document.workspace_id).first()
                if department and department.head_user_id != member.manager_user_id:
                    steps.append({'step': 2, 'approver_id': department.head_user_id, 'status': 'pending'})
        if not isinstance(steps, list) or not steps:
            return None, 'steps must be a non-empty list'
        for index, step in enumerate(steps, start=1):
            step.setdefault('step', index)
            step.setdefault('status', 'pending')
            if not step.get('approver_id'):
                return None, 'Every approval step requires approver_id'
        approval = Approval(
            workspace_id=document.workspace_id, document_id=document.id,
            title=document.title, approval_type='document', initiator_id=user_id,
            steps=steps, history=[],
        )
        document.status = 'reviewing'
        db.session.add(approval)
        # 通知第一级的所有审批人（直属领导并行审批时人人都会收到）
        first_step_no = min((step.get('step') or 1) for step in steps)
        for step in steps:
            if step.get('step') == first_step_no:
                organization_service.notify(document.workspace_id, step['approver_id'], 'approval',
                    f'待审批：{document.title}', '请查看公文正文并完成审批。', 'approval', approval.id)
        db.session.commit()
        return approval.to_dict(), None

    def publish(self, document_id, user_id):
        document = OfficialDocument.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return None, 'Document not found'
        if document.status != 'approved':
            return None, 'Only approved documents can be published'
        document.status = 'published'
        document.published_at = datetime.utcnow()
        for recipient in document.recipients or []:
            if not isinstance(recipient, dict) or not recipient.get('user_id'):
                continue
            receipt = DocumentReceipt.query.filter_by(document_id=document.id, recipient_id=recipient['user_id']).first()
            if not receipt:
                receipt = DocumentReceipt(
                    document_id=document.id, workspace_id=document.workspace_id,
                    recipient_id=recipient['user_id'], recipient_name=recipient.get('display_name', ''),
                )
                db.session.add(receipt)
            organization_service.notify(document.workspace_id, recipient['user_id'], 'document_delivery',
                f'已发布公文：{document.title}', '请查看公文正文并确认已知悉。', 'document', document.id)
        db.session.commit()
        return document.to_dict(), None

    def confirm_receipt(self, document_id, user_id):
        document = OfficialDocument.query.get(document_id)
        if not document or document.status != 'published' or not organization_service.can_access(document.workspace_id, user_id):
            return None, 'Published document not found'
        receipt = DocumentReceipt.query.filter_by(document_id=document_id, recipient_id=user_id).first()
        if not receipt:
            return None, 'You are not a recipient of this document'
        now = datetime.utcnow()
        if not receipt.read_at:
            receipt.read_at = now
        receipt.confirmed_at = receipt.confirmed_at or now
        db.session.commit()
        return receipt.to_dict(), None


document_service = DocumentService()
