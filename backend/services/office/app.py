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
