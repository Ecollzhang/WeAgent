import time
from app.models.deployment import Deployment
from app.repositories.base_repo import BaseRepository
from app.services.message_service import broadcast


class DeploymentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Deployment)

    def get_by_conversation(self, conversation_id):
        return Deployment.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Deployment.created_at.desc()).all()


deploy_repo = DeploymentRepository()


def run_mock_deploy(conversation_id, deploy_id):
    """Synchronous mock deploy — broadcasts progress via SSE, called from _mock_agent_response."""
    steps = [
        (3, 10, '正在打包源码...'),
        (2, 30, '正在上传到服务器...'),
        (3, 60, '正在构建部署环境...'),
        (2, 85, '正在配置访问域名...'),
        (1, 100, '部署完成'),
    ]
    logs = []
    from app import db
    for delay, progress, log in steps:
        time.sleep(delay)
        logs.append(log)
        deploy = deploy_repo.get_by_id(deploy_id)
        if not deploy:
            return
        deploy.status = 'deploying' if progress < 100 else 'success'
        deploy.progress = progress
        deploy.logs = logs
        if progress == 100:
            deploy.preview_url = f'https://preview-{deploy_id[:8]}.weagent.dev'
        db.session.commit()

        broadcast(conversation_id, {
            '_type': 'deploy_status',
            'deploy_id': deploy_id,
            'status': deploy.status,
            'progress': progress,
            'logs': logs,
            'preview_url': deploy.preview_url,
            'deploy_url': deploy.deploy_url,
        })


class DeployService:
    def create(self, conversation_id, artifact_id=None, source_type='webpage'):
        deploy = deploy_repo.create(
            conversation_id=conversation_id,
            artifact_id=artifact_id,
            status='pending',
            provider='mock',
            progress=0,
            logs=[],
            source_type=source_type,
        )
        return deploy.to_dict(), None

    def get_by_id(self, deploy_id):
        deploy = deploy_repo.get_by_id(deploy_id)
        if not deploy:
            return None, 'Deployment not found'
        return deploy.to_dict(), None

    def get_by_conversation(self, conversation_id):
        deploys = deploy_repo.get_by_conversation(conversation_id)
        return [d.to_dict() for d in deploys], None


deploy_service = DeployService()
