"""WeAgent 智慧办公领域服务.

启动方式:
    cd services/office
    python app.py
"""
import sys
import os

from config import Config

# 确保能导入共享核心 app 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.domain_base import DomainServiceBase
from extensions import db
from flask import jsonify
from sqlalchemy import inspect, text

service = DomainServiceBase(Config, db_instance=db)
app = service.app

from controllers.approval_controller import approval_bp
from controllers.document_controller import document_bp
from controllers.meeting_controller import meeting_bp
from controllers.schedule_controller import schedule_bp
from controllers.template_controller import template_bp
from controllers.organization_controller import organization_bp

app.register_blueprint(meeting_bp, url_prefix='/api/office/meetings')
app.register_blueprint(schedule_bp, url_prefix='/api/office/schedules')
app.register_blueprint(document_bp, url_prefix='/api/office/documents')
app.register_blueprint(template_bp, url_prefix='/api/office/document-templates')
app.register_blueprint(approval_bp, url_prefix='/api/office/approvals')
app.register_blueprint(organization_bp, url_prefix='/api/office/organization')


def _build_office_spec():
    """Expose the Office API contract used by sandbox agents for service discovery."""
    return {
        'service': 'office',
        'version': '1.0.0',
        'description': '智慧办公领域服务，提供会议、行动项、日程、公文、审批和组织协同能力。',
        'base_url': f'http://host.docker.internal:{Config.PORT}',
        'status': 'healthy',
        'capabilities': [
            {'name': '会议与行动项', 'description': '查询会议、纪要和负责人待办'},
            {'name': '办公日程', 'description': '查询个人会议、任务和提醒'},
            {'name': '公文与审批', 'description': '查询公文、模板及待审批事项'},
            {'name': '组织协同', 'description': '查询部门、小组、成员和通知'},
        ],
        'popular_endpoints': [
            {'method': 'GET', 'path': '/api/office/meetings?workspace_id=<workspace_id>', 'description': '查询当前工作空间可见的会议'},
            {'method': 'GET', 'path': '/api/office/schedules?workspace_id=<workspace_id>', 'description': '查询我的日程与待办'},
            {'method': 'GET', 'path': '/api/office/documents?workspace_id=<workspace_id>', 'description': '查询可见公文及签收状态'},
            {'method': 'GET', 'path': '/api/office/approvals?workspace_id=<workspace_id>', 'description': '查询待我处理或历史审批'},
            {'method': 'GET', 'path': '/api/office/organization?workspace_id=<workspace_id>', 'description': '查询部门、小组和成员关系'},
            {'method': 'POST', 'path': '/api/office/meetings', 'description': '创建会议；仅在用户明确确认后调用'},
        ],
        'all_endpoints': [],
    }


@app.route('/api/office/spec')
def api_spec():
    """Return the Office service contract for Agent prompt injection and API tools."""
    return jsonify(_build_office_spec())

if __name__ == '__main__':
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        columns = {item['name'] for item in inspect(db.engine).get_columns('office_meetings')}
        document_columns = {item['name'] for item in inspect(db.engine).get_columns('office_documents')}
        schedule_columns = {item['name'] for item in inspect(db.engine).get_columns('office_schedules')}
        if 'meeting_link' not in columns:
            db.session.execute(text("ALTER TABLE office_meetings ADD COLUMN meeting_link VARCHAR(1000) DEFAULT ''"))
        if 'materials' not in columns:
            db.session.execute(text("ALTER TABLE office_meetings ADD COLUMN materials JSON NULL"))
        if 'recipients' not in document_columns:
            db.session.execute(text("ALTER TABLE office_documents ADD COLUMN recipients JSON NULL"))
        if 'approvers' not in document_columns:
            db.session.execute(text("ALTER TABLE office_documents ADD COLUMN approvers JSON NULL"))
        if 'document_id' not in schedule_columns:
            db.session.execute(text("ALTER TABLE office_schedules ADD COLUMN document_id VARCHAR(36) NULL"))
        db.session.execute(text(
            "ALTER TABLE office_schedules MODIFY COLUMN status "
            "ENUM('pending','in_progress','done','cancelled') NOT NULL DEFAULT 'pending'"
        ))
        if 'meeting_link' not in columns or 'materials' not in columns or 'recipients' not in document_columns or 'approvers' not in document_columns or 'document_id' not in schedule_columns:
            db.session.commit()
        from seed_data import seed_system_templates
        seed_system_templates()
    print(f'[WeAgent] 智慧办公服务启动 → http://127.0.0.1:{Config.PORT}')
    service.run(debug=True)
