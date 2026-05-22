import threading
from app.repositories.conversation_repo import conversation_repo
from app.repositories.message_repo import message_repo
from app.repositories.agent_repo import agent_repo
from app.services.message_service import message_service


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

    def _invoke_agent(self, agent, conversation_id, user_content):
        """Invoke a single agent and save its response."""
        from app.adapters import get_adapter

        try:
            adapter_class = get_adapter(agent.adapter_name)
            adapter = adapter_class()
            response_content = adapter.send_prompt(
                prompt=user_content,
                context={'system_prompt': agent.system_prompt, 'agent_name': agent.name}
            )

            # Save agent's response as a message
            if response_content:
                message_service.send_message(
                    conversation_id=conversation_id,
                    sender_type='agent',
                    sender_id=agent.id,
                    content=response_content,
                    message_type='text'
                )
        except Exception as e:
            # Log error but don't crash
            import logging
            logging.error(f'Agent {agent.name} invocation failed: {str(e)}')

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

        self._invoke_agent(agent, conversation_id, user_message.content)


orchestrator_service = OrchestratorService()
