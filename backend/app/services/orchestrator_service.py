import threading
import logging
from flask import current_app, has_app_context
from app.adapters.factory import AgentAdapterFactory
from app.adapters.types import AgentRequest, resolve_workspace_path
from app.repositories.conversation_repo import conversation_repo
from app.repositories.message_repo import message_repo
from app.repositories.agent_repo import agent_repo
from app.services.conversation_context_service import conversation_context_service
from app.services.message_service import broadcast, message_service


class OrchestratorService:
    """Master Agent Orchestrator.

    In group chat mode, this service:
    1. Receives a user message
    2. Determines which agents should respond
    3. Dispatches tasks to agent adapters
    4. Aggregates results back into the conversation
    """

    def dispatch_to_agents(self, conversation_id, user_message_id):
        """Dispatch user message to relevant agents in a group conversation.

        This runs in a background thread to avoid blocking the API response.
        """
        try:
            conversation = conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return

            # Get agent participants
            participants = conversation_repo.get_conversation_participants(conversation_id)
            agent_participants = [p for p in participants if p.participant_type == 'agent']

            if not agent_participants:
                return

            user_message = message_repo.get_by_id(user_message_id)
            if not user_message:
                return

            app = current_app._get_current_object() if has_app_context() else None

            # Dispatch to each agent in parallel
            threads = []
            for participant in agent_participants:
                agent = agent_repo.get_by_id(participant.participant_id)
                if not agent:
                    continue

                thread = threading.Thread(
                    target=self._invoke_agent_in_context,
                    args=(app, agent, conversation_id, user_message.content, user_message.id)
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        finally:
            broadcast(conversation_id, {'_type': 'agent_done'})

    def _invoke_agent(self, agent, conversation_id, user_content, user_message_id=None):
        """Invoke a single agent and save its response."""
        try:
            adapter = AgentAdapterFactory.create(agent.adapter_name)
            request = self._build_agent_request(
                agent,
                conversation_id,
                user_content,
                user_message_id=user_message_id,
            )
            response_parts = []
            completed_content = None

            for event in adapter.stream(request):
                broadcast(conversation_id, event)
                if event.get('type') == 'artifact.created':
                    conversation_context_service.record_event(conversation_id, event)

                event_type = event.get('type')
                if event_type == 'message.delta':
                    response_parts.append(event.get('content', ''))
                elif event_type == 'message.completed':
                    completed_content = event.get('content') or ''.join(response_parts)
                elif event_type == 'agent.failed':
                    logging.error(
                        'Agent %s invocation failed: %s',
                        agent.name,
                        event.get('message') or event.get('content') or event,
                    )

            response_content = completed_content or ''.join(response_parts)

            if response_content:
                message_service.send_message(
                    conversation_id=conversation_id,
                    sender_type='agent',
                    sender_id=agent.id,
                    content=response_content,
                    message_type='text'
                )
        except Exception as e:
            logging.error(f'Agent {agent.name} invocation failed: {str(e)}')
            request = self._build_agent_request(
                agent,
                conversation_id,
                user_content,
                user_message_id=user_message_id,
            )
            broadcast(
                conversation_id,
                {
                    'schemaVersion': 'v1',
                    'type': 'agent.failed',
                    'runId': request.run_id,
                    'conversationId': conversation_id,
                    'agentId': agent.id,
                    'agentName': agent.name,
                    'message': str(e),
                },
            )

    def _invoke_agent_in_context(self, app, agent, conversation_id, user_content, user_message_id=None):
        if app is None:
            if user_message_id is None:
                self._invoke_agent(agent, conversation_id, user_content)
            else:
                self._invoke_agent(agent, conversation_id, user_content, user_message_id)
            return
        with app.app_context():
            if user_message_id is None:
                self._invoke_agent(agent, conversation_id, user_content)
            else:
                self._invoke_agent(agent, conversation_id, user_content, user_message_id)

    def _build_agent_request(self, agent, conversation_id, user_content, user_message_id=None):
        agent_config = agent.config if isinstance(getattr(agent, 'config', None), dict) else {}
        workspace_path = agent_config.get('workspace_path') or resolve_workspace_path()
        context = conversation_context_service.build_context(
            conversation_id,
            current_user_message_id=user_message_id,
        )
        prompt = conversation_context_service.format_prompt(
            system_prompt=agent.system_prompt,
            context=context,
            current_user_message=user_content,
        )
        return AgentRequest(
            prompt=prompt,
            conversation_id=conversation_id,
            agent_id=agent.id,
            agent_name=agent.name,
            system_prompt=agent.system_prompt,
            conversation_history=context.get('transcript'),
            workspace_path=workspace_path,
            metadata={
                'adapter_name': agent.adapter_name,
                'agent_type': getattr(agent, 'agent_type', None),
                'raw_user_message': user_content,
                'context_summary': context.get('summary'),
            },
        )

    def process_single_agent_chat(self, conversation_id, user_message_id, agent_id):
        """Process a single-agent conversation (one user + one agent)."""
        conversation = conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return

        user_message = message_repo.get_by_id(user_message_id)
        if not user_message:
            return

        agent = agent_repo.get_by_id(agent_id)
        if not agent:
            return

        try:
            self._invoke_agent(agent, conversation_id, user_message.content, user_message.id)
        finally:
            broadcast(conversation_id, {'_type': 'agent_done'})


orchestrator_service = OrchestratorService()
