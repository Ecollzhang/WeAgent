from app import db
from app.models.agent_run import AgentRun
from app.utils.timezone import beijing_now


class AgentRunService:
    """Persistence helpers for formal chat agent executions."""

    def create_run(self, conversation_id, round_id, message_id, agent_id,
                   sandbox_session_id=None, status='running'):
        run = AgentRun(
            conversation_id=conversation_id,
            round_id=round_id,
            message_id=message_id,
            agent_id=agent_id,
            sandbox_session_id=sandbox_session_id,
            status=status,
            started_at=beijing_now(),
        )
        db.session.add(run)
        db.session.commit()
        return run

    def find_active_run(self, conversation_id, agent_id):
        return AgentRun.query.filter(
            AgentRun.conversation_id == conversation_id,
            AgentRun.agent_id == agent_id,
            AgentRun.status.in_(('pending', 'running')),
        ).order_by(AgentRun.created_at.desc()).first()

    def finish_run(self, run, status='done', error=None, last_seq=None):
        run.status = status
        run.finished_at = beijing_now()
        if error:
            run.error = error
        if last_seq is not None:
            run.last_seq = last_seq
        db.session.commit()
        return run

    def update_last_seq(self, run, seq):
        if seq is not None:
            run.last_seq = max(run.last_seq or 0, int(seq or 0))
            db.session.commit()
        return run


agent_run_service = AgentRunService()
