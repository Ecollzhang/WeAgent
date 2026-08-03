"""评论业务逻辑."""
from database import db
from models.comment import RdComment
from models.activity import RdActivityLog
from datetime import datetime


class CommentService:

    def list_comments(self, project_id, target_type=None, target_id=None):
        q = RdComment.query.filter_by(project_id=project_id, parent_id=None)
        if target_type:
            q = q.filter_by(target_type=target_type)
        if target_id:
            q = q.filter_by(target_id=target_id)
        return [c.to_dict() for c in q.order_by(RdComment.created_at.asc()).all()]

    def create_comment(self, project_id, data, user_id=None):
        comment = RdComment(
            project_id=project_id,
            target_type=data['target_type'],
            target_id=data['target_id'],
            parent_id=data.get('parent_id'),
            content=data['content'],
            content_type=data.get('content_type', 'markdown'),
            author_id=user_id,
        )
        db.session.add(comment)
        self._log(db.session, project_id, data['target_type'], data['target_id'],
                  'commented', user_id)
        db.session.commit()
        return comment.to_dict()

    def update_comment(self, comment_id, data, user_id=None):
        comment = RdComment.query.filter_by(id=comment_id).first()
        if not comment:
            return None
        if 'content' in data:
            comment.content = data['content']
        if 'is_pinned' in data:
            comment.is_pinned = data['is_pinned']
        db.session.commit()
        return comment.to_dict()

    def delete_comment(self, comment_id, user_id=None):
        comment = RdComment.query.filter_by(id=comment_id).first()
        if not comment:
            return False
        comment.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def _log(self, sess, project_id, target_type, target_id, action, actor_id,
             old_value=None, new_value=None):
        log = RdActivityLog(
            project_id=project_id, target_type=target_type, target_id=target_id,
            action=action, actor_id=actor_id,
            old_value=old_value, new_value=new_value,
        )
        sess.add(log)


comment_service = CommentService()
