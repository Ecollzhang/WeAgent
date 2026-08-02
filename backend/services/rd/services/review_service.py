"""代码审查业务逻辑."""
from datetime import datetime
from database import db
from models.review import RdReview, RdReviewIssue
from models.activity import RdActivityLog


class ReviewService:

    def list_reviews(self, project_id, status=None, language=None):
        """查询审查列表."""
        q = RdReview.query.filter_by(project_id=project_id)
        if status:
            q = q.filter_by(status=status)
        if language:
            q = q.filter_by(language=language)
        return [r.to_dict() for r in q.order_by(RdReview.created_at.desc()).all()]

    def get_review(self, review_id):
        """获取审查详情（含 issues）."""
        r = RdReview.query.filter_by(id=review_id).first()
        return r.to_dict() if r else None

    def create_review(self, project_id, data, user_id=None):
        """创建审查记录."""
        review = RdReview(
            project_id=project_id,
            repo_id=data.get('repo_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            code_content=data.get('code_content', ''),
            file_paths=data.get('file_paths', []),
            language=data.get('language', ''),
            branch=data.get('branch'),
            commit_sha=data.get('commit_sha'),
            review_method=data.get('review_method', 'script'),
            status='reviewing',
            created_by=user_id,
        )
        db.session.add(review)
        db.session.flush()  # 获取 review.id

        # 填充审查结果（issues + scores）
        if data.get('issues'):
            overall_score = data.get('overall_score', 0)
            review.overall_score = overall_score
            review.scores = data.get('scores', {})
            review.summary = data.get('summary', '')
            review.status = 'completed'
            review.reviewed_at = datetime.utcnow()

            for issue_data in data.get('issues') or []:
                issue = RdReviewIssue(
                    review_id=review.id,
                    severity=issue_data.get('severity', 'warning'),
                    category=issue_data.get('category', 'style'),
                    file_path=issue_data.get('file_path'),
                    line_start=issue_data.get('line_start'),
                    line_end=issue_data.get('line_end'),
                    title=issue_data.get('title', ''),
                    description=issue_data.get('description', ''),
                    suggestion=issue_data.get('suggestion', ''),
                    code_snippet=issue_data.get('code_snippet', ''),
                    fixed_snippet=issue_data.get('fixed_snippet', ''),
                )
                db.session.add(issue)

        self._log(db.session, project_id, 'review', review.id, 'created',
                  user_id, new_value={'title': review.title})
        db.session.commit()
        return review.to_dict()

    def update_review(self, review_id, data):
        """更新审查（如重新审查）."""
        r = RdReview.query.filter_by(id=review_id).first()
        if not r:
            return None

        if 'overall_score' in data:
            r.overall_score = data['overall_score']
        if 'scores' in data:
            r.scores = data['scores']
        if 'summary' in data:
            r.summary = data['summary']
        if 'status' in data:
            r.status = data['status']
            if data['status'] == 'completed':
                r.reviewed_at = datetime.utcnow()

        # 替换 issues
        if 'issues' in data:
            RdReviewIssue.query.filter_by(review_id=review_id).delete()
            for issue_data in data['issues']:
                issue = RdReviewIssue(
                    review_id=review_id,
                    severity=issue_data.get('severity', 'warning'),
                    category=issue_data.get('category', 'style'),
                    file_path=issue_data.get('file_path'),
                    line_start=issue_data.get('line_start'),
                    line_end=issue_data.get('line_end'),
                    title=issue_data.get('title', ''),
                    description=issue_data.get('description', ''),
                    suggestion=issue_data.get('suggestion', ''),
                    code_snippet=issue_data.get('code_snippet', ''),
                    fixed_snippet=issue_data.get('fixed_snippet', ''),
                )
                db.session.add(issue)

        db.session.commit()
        return r.to_dict()

    def update_issue(self, issue_id, data):
        """更新 issue 状态."""
        issue = RdReviewIssue.query.filter_by(id=issue_id).first()
        if not issue:
            return None
        if 'status' in data:
            issue.status = data['status']
        if 'suggestion' in data:
            issue.suggestion = data['suggestion']
        if 'fixed_snippet' in data:
            issue.fixed_snippet = data['fixed_snippet']
        db.session.commit()
        return issue.to_dict()

    def delete_review(self, review_id):
        """删除审查记录."""
        r = RdReview.query.filter_by(id=review_id).first()
        if not r:
            return False
        db.session.delete(r)
        db.session.commit()
        return True

    def _log(self, sess, project_id, target_type, target_id, action, actor_id,
             old_value=None, new_value=None):
        log = RdActivityLog(
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
        )
        sess.add(log)


review_service = ReviewService()
