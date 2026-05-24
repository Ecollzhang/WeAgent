import threading
import logging
from app.adapters.factory import AgentAdapterFactory
from app.adapters.types import AgentRequest, resolve_workspace_path
from app.repositories.conversation_repo import conversation_repo
from app.repositories.message_repo import message_repo
from app.repositories.agent_repo import agent_repo
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

            # Dispatch to each agent in parallel
            threads = []
            for participant in agent_participants:
                agent = agent_repo.get_by_id(participant.participant_id)
                if not agent:
                    continue

                thread = threading.Thread(
                    target=self._invoke_agent,
                    args=(agent, conversation_id, user_message.content)
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        finally:
            broadcast(conversation_id, {'_type': 'agent_done'})

    def _invoke_agent(self, agent, conversation_id, user_content):
        """Invoke a single agent and save its response."""
        try:
            adapter = AgentAdapterFactory.create(agent.adapter_name)
            request = self._build_agent_request(agent, conversation_id, user_content)
            response_parts = []
            completed_content = None

            for event in adapter.stream(request):
                broadcast(conversation_id, event)

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
            request = self._build_agent_request(agent, conversation_id, user_content)
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

    def _build_agent_request(self, agent, conversation_id, user_content):
        agent_config = agent.config if isinstance(getattr(agent, 'config', None), dict) else {}
        workspace_path = agent_config.get('workspace_path') or resolve_workspace_path()
        return AgentRequest(
            prompt=user_content,
            conversation_id=conversation_id,
            agent_id=agent.id,
            agent_name=agent.name,
            system_prompt=agent.system_prompt,
            workspace_path=workspace_path,
            metadata={
                'adapter_name': agent.adapter_name,
                'agent_type': getattr(agent, 'agent_type', None),
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
            self._invoke_agent(agent, conversation_id, user_message.content)
        finally:
            broadcast(conversation_id, {'_type': 'agent_done'})


orchestrator_service = OrchestratorService()
