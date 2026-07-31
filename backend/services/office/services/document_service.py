"""Official document and template business logic."""
from datetime import datetime

from extensions import db
from models.approval import Approval
from models.document_template import DocumentTemplate
from models.meeting import Meeting
from models.official_document import OfficialDocument
from services.helpers import page_args
from services.organization_service import organization_service


class DocumentService:
    """Manage office documents, templates and submission for approval."""
    VALID_TYPES = ('notice', 'report', 'request', 'letter', 'minutes', 'other')

    def list_documents(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        if not workspace_id:
            return None, 'workspace_id is required'
        page, page_size = page_args(params)
        query = OfficialDocument.query.filter_by(workspace_id=workspace_id).filter(
            (OfficialDocument.user_id == user_id) | (OfficialDocument.status == 'published')
        )
        if params.get('status'):
            query = query.filter_by(status=params['status'])
        pagination = query.order_by(OfficialDocument.updated_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
        }, None

    def get_document(self, document_id, user_id):
        document = OfficialDocument.query.get(document_id)
        if document and document.user_id != user_id and document.status != 'published':
            related = Approval.query.filter_by(document_id=document.id).all()
            if not any(user_id == step.get('approver_id') for item in related for step in (item.steps or [])):
                document = None
        if not document:
            return None, 'Document not found'
        result = document.to_dict()
        result['approvals'] = [
            item.to_dict()
            for item in Approval.query.filter_by(document_id=document.id).order_by(Approval.created_at.desc()).all()
        ]
        return result, None

    def create_document(self, user_id, data):
        workspace_id = (data.get('workspace_id') or '').strip()
        title = (data.get('title') or '').strip()
        document_type = data.get('document_type', 'notice')
        if not workspace_id:
            return None, 'workspace_id is required'
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
        document = OfficialDocument(
            workspace_id=workspace_id, user_id=user_id, meeting_id=data.get('meeting_id'),
            title=title, document_type=document_type, content=content, template_id=template_id,
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
        for field in ('title', 'content', 'template_id', 'meeting_id'):
            if field in data:
                setattr(document, field, data[field])
        if 'document_type' in data:
            if data['document_type'] not in self.VALID_TYPES:
                return None, 'Invalid document_type'
            document.document_type = data['document_type']
        db.session.commit()
        return document.to_dict(), None

    def list_templates(self, user_id, params):
        workspace_id = (params.get('workspace_id') or '').strip()
        if not workspace_id:
            return None, 'workspace_id is required'
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
            if not member or not member.manager_user_id:
                return None, '请先在组织架构中设置直属领导后再提交审批'
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
        organization_service.notify(document.workspace_id, steps[0]['approver_id'], 'approval',
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
        db.session.commit()
        return document.to_dict(), None


document_service = DocumentService()
