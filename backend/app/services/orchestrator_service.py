import logging
from flask import current_app, has_app_context

from app.repositories.message_repo import message_repo
from app.services.message_service import broadcast, message_service


class OrchestratorService:
    """Deprecated compatibility facade.

    Host/local adapters are no longer an execution path. Agent execution is
    owned by message_service, which dispatches to the sandbox container and its
    provider runners (Claude/Codex/OpenCode).
    """

    def dispatch_to_agents(self, conversation_id, user_message_id):
        user_message = message_repo.get_by_id(user_message_id)
        if not user_message:
            return

        app = current_app._get_current_object() if has_app_context() else None
        try:
            if app is None:
                logging.warning(
                    "orchestrator_service.dispatch_to_agents ignored: no Flask app context"
                )
                return
            with app.app_context():
                message_service._dispatch_agent_sandbox(
                    app,
                    conversation_id,
                    user_message.content,
                    user_message.id,
                )
        finally:
            broadcast(conversation_id, {"_type": "agent_done"})

    def process_single_agent_chat(self, conversation_id, user_message_id, agent_id):
        self.dispatch_to_agents(conversation_id, user_message_id)


orchestrator_service = OrchestratorService()
