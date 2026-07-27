"""RAG 文档分块模型."""
import uuid
from sqlalchemy.dialects.mysql import JSON
from .database import db


class Chunk(db.Model):
    __tablename__ = 'rag_chunks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(
        db.String(36),
        db.ForeignKey('rag_documents.id', ondelete='CASCADE'),
        nullable=False,
    )
    chunk_index = db.Column(db.Integer, nullable=False, comment='分块序号')

    content = db.Column(db.Text, nullable=False, comment='分块文本')
    token_count = db.Column(db.Integer, default=0)

    vector_id = db.Column(db.String(200), nullable=True, comment='ChromaDB 中对应的向量ID')

    page_number = db.Column(db.Integer, nullable=True, comment='来源页码')
    extra_meta = db.Column('extra_meta', JSON, nullable=True)

    document = db.relationship('Document', back_populates='chunks')

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'token_count': self.token_count,
            'vector_id': self.vector_id,
            'page_number': self.page_number,
            'extra_meta': self.extra_meta,
        }
