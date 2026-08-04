"""项目文件模型 — Agent 生成的代码产物."""
import uuid
from database import db


def gen_uuid():
    return str(uuid.uuid4())


class RdProjectFile(db.Model):
    __tablename__ = 'rd_project_files'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    conversation_id = db.Column(db.String(36), nullable=True, comment='来源会话')
    file_name = db.Column(db.String(500), nullable=False, comment='文件名')
    file_path = db.Column(db.String(1000), nullable=False, comment='文件路径')
    content = db.Column(db.Text, nullable=True, comment='文件内容')
    file_type = db.Column(db.String(50), nullable=True, comment='py/js/vue/sql等')
    size = db.Column(db.Integer, default=0, comment='文件大小(字节)')
    version = db.Column(db.Integer, default=1, comment='版本号')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    project = db.relationship('RdProject', back_populates='files')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'conversation_id': self.conversation_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'size': self.size,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
