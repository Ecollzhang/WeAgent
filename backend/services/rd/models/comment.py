"""评论模型 — 统一用于需求/Bug/迭代."""
from database import db
from models.project import gen_uuid


class RdComment(db.Model):
    __tablename__ = 'rd_comments'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey('rd_projects.id', ondelete='CASCADE'), nullable=False
    )
    target_type = db.Column(
        db.Enum('requirement', 'bug', 'iteration', name='comment_target_type'),
        nullable=False,
    )
    target_id = db.Column(db.String(36), nullable=False, comment='目标ID')
    parent_id = db.Column(
        db.String(36), db.ForeignKey('rd_comments.id', ondelete='CASCADE'),
        nullable=True, comment='父评论ID, 支持嵌套回复'
    )
    content = db.Column(db.Text, nullable=False, comment='评论内容(Markdown)')
    content_type = db.Column(
        db.Enum('text', 'markdown', 'system', name='comment_content_type'),
        default='markdown',
    )
    author_id = db.Column(db.String(36), nullable=True, comment='作者ID')
    is_pinned = db.Column(db.Boolean, default=False, comment='是否置顶')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True, comment='软删除时间')

    # 自引用关系(嵌套回复)
    replies = db.relationship(
        'RdComment', backref=db.backref('parent', remote_side=[id]),
        lazy='joined', order_by='RdComment.created_at.asc()'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'parent_id': self.parent_id,
            'content': self.content,
            'content_type': self.content_type,
            'author_id': self.author_id,
            'is_pinned': self.is_pinned,
            'replies': [r.to_dict() for r in self.replies if r.deleted_at is None],
            'is_deleted': self.deleted_at is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
