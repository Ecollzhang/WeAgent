"""构建管理业务逻辑."""
from datetime import datetime
from database import db
from models.build import RdBuild, RdBuildStep


class BuildService:

    def list_builds(self, project_id, status=None, branch=None):
        """查询构建列表."""
        q = RdBuild.query.filter_by(project_id=project_id)
        if status:
            q = q.filter_by(status=status)
        if branch:
            q = q.filter_by(branch=branch)
        return [r.to_dict() for r in q.order_by(RdBuild.created_at.desc()).all()]

    def get_build(self, build_id):
        """获取构建详情（含步骤）."""
        b = RdBuild.query.filter_by(id=build_id).first()
        return b.to_dict() if b else None

    def create_build(self, project_id, data, user_id=None):
        """创建构建记录."""
        # 自增 build_number
        last = RdBuild.query.filter_by(project_id=project_id) \
            .order_by(RdBuild.build_number.desc()).first()
        build_number = (last.build_number + 1) if last else 1

        build = RdBuild(
            project_id=project_id,
            build_number=build_number,
            build_type=data.get('build_type', 'manual'),
            status=data.get('status', 'pending'),
            commit_hash=data.get('commit_hash'),
            commit_message=data.get('commit_message'),
            branch=data.get('branch'),
            started_at=datetime.utcnow() if data.get('status') == 'running' else None,
            duration_seconds=data.get('duration_seconds'),
            created_by=user_id or data.get('created_by'),
            error_summary=data.get('error_summary'),
            preview_url=data.get('preview_url'),
            artifacts=data.get('artifacts', []),
            repo_id=data.get('repo_id'),
            workflow_id=data.get('workflow_id'),
            github_run_id=data.get('github_run_id'),
        )
        db.session.add(build)
        db.session.flush()

        for s in (data.get('steps') or []):
            step = RdBuildStep(
                build_id=build.id,
                step_name=s.get('step_name', ''),
                step_order=s.get('step_order', 0),
                status=s.get('status', 'pending'),
                command=s.get('command'),
                duration_seconds=s.get('duration_seconds'),
                log=s.get('log'),
            )
            db.session.add(step)

        db.session.commit()
        return build.to_dict()

    def update_build(self, build_id, data):
        """更新构建状态/步骤（用于模拟构建流程）."""
        b = RdBuild.query.filter_by(id=build_id).first()
        if not b:
            return None

        for field in ('status', 'duration_seconds', 'error_summary', 'preview_url', 'artifacts',
                       'repo_id', 'workflow_id', 'github_run_id',
                       'commit_hash', 'commit_message', 'branch'):
            if field in data:
                setattr(b, field, data[field])

        if 'status' in data:
            if data['status'] == 'running' and not b.started_at:
                b.started_at = datetime.utcnow()
            elif data['status'] in ('success', 'failed', 'cancelled'):
                b.finished_at = datetime.utcnow()

        if 'steps' in data:
            RdBuildStep.query.filter_by(build_id=build_id).delete()
            for s in data['steps']:
                step = RdBuildStep(
                    build_id=build_id,
                    step_name=s.get('step_name', ''),
                    step_order=s.get('step_order', 0),
                    status=s.get('status', 'pending'),
                    command=s.get('command'),
                    duration_seconds=s.get('duration_seconds'),
                    log=s.get('log'),
                )
                db.session.add(step)

        db.session.commit()
        return b.to_dict()

    def get_build_log(self, build_id, step_order=None):
        """获取构建日志."""
        b = RdBuild.query.filter_by(id=build_id).first()
        if not b:
            return None
        q = RdBuildStep.query.filter_by(build_id=build_id)
        if step_order is not None:
            q = q.filter_by(step_order=step_order)
        steps = q.order_by(RdBuildStep.step_order).all()
        return {
            'build_id': build_id,
            'status': b.status,
            'steps': [{'step_name': s.step_name, 'step_order': s.step_order,
                       'status': s.status, 'log': s.log} for s in steps],
        }

    def cancel_build(self, build_id):
        """取消构建."""
        b = RdBuild.query.filter_by(id=build_id).first()
        if not b:
            return None
        if b.status not in ('pending', 'running'):
            return None
        b.status = 'cancelled'
        b.finished_at = datetime.utcnow()
        db.session.commit()
        return b.to_dict()

    def get_artifacts(self, build_id):
        """获取构建产物列表."""
        b = RdBuild.query.filter_by(id=build_id).first()
        if not b:
            return None
        return {
            'build_id': build_id,
            'artifacts': b.artifacts or [],
            'preview_url': b.preview_url,
        }

    def delete_build(self, build_id):
        """删除构建记录."""
        b = RdBuild.query.filter_by(id=build_id).first()
        if not b:
            return False
        db.session.delete(b)
        db.session.commit()
        return True


build_service = BuildService()
