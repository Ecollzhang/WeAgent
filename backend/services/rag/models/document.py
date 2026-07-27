"""RAG 文档模型."""
import uuid
from sqlalchemy.dialects.mysql import JSON
from .database import db


def gen_uuid():
    return str(uuid.uuid4())


class Document(db.Model):
    __tablename__ = 'rag_documents'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), nullable=False, comment='上传者')
    workspace_id = db.Column(db.String(36), nullable=True, comment='所属工作空间')
    domain = db.Column(db.String(50), nullable=False, comment='rd / edu / office')

    name = db.Column(db.String(500), nullable=False, comment='文档名称')
    source_type = db.Column(
        db.Enum('upload', 'url', 'scrape', name='rag_source_type'),
        nullable=False,
    )
    source_url = db.Column(db.String(2000), nullable=True, comment='来源URL')
    file_type = db.Column(db.String(50), nullable=True, comment='pdf/txt/md/docx/csv等')
    file_size = db.Column(db.BigInteger, nullable=True, comment='文件字节数')

    status = db.Column(
        db.Enum('pending', 'processing', 'ready', 'error', name='rag_doc_status'),
        default='pending',
    )
    chunk_count = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)

    description = db.Column(db.Text, nullable=True, comment='用户备注')
    extra_meta = db.Column('extra_meta', JSON, nullable=True, comment='原始网页标题/作者等')

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    chunks = db.relationship(
        'Chunk', back_populates='document', cascade='all, delete-orphan', lazy='dynamic'
    )

    def to_dict(self, include_chunks=False):
        # 列表接口不需要 _text 字段（内部使用），避免响应体积过大
        meta = dict(self.extra_meta or {})
        meta.pop('_text', None)

        data = {
            'id': self.id,
            'user_id': self.user_id,
            'workspace_id': self.workspace_id,
            'domain': self.domain,
            'name': self.name,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'status': self.status,
            'chunk_count': self.chunk_count,
            'total_tokens': self.total_tokens,
            'description': self.description,
            'extra_meta': meta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_chunks:
            data['chunks'] = [c.to_dict() for c in self.chunks.order_by('chunk_index').all()]
        return data
