from flask import request
from flask_socketio import join_room, leave_room, emit
from app import socketio
from app.services.message_service import message_service
from app.services.orchestrator_service import orchestrator_service


@socketio.on('connect')
def handle_connect():
    """Client connected."""
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected."""
    pass


@socketio.on('join')
def handle_join(data):
    """Join a conversation room."""
    room = data.get('conversation_id')
    if room:
        join_room(room)
        emit('joined', {'conversation_id': room}, room=room)


@socketio.on('leave')
def handle_leave(data):
    """Leave a conversation room."""
    room = data.get('conversation_id')
    if room:
        leave_room(room)
        emit('left', {'conversation_id': room}, room=room)


@socketio.on('send_message')
def handle_send_message(data):
    """Handle real-time message sending.

    Expected data:
    {
        'conversation_id': '...',
        'sender_type': 'user',
        'sender_id': '...',
        'content': '...',
        'message_type': 'text',
        'parent_message_id': null
    }
    """
    conversation_id = data.get('conversation_id')
    sender_type = data.get('sender_type', 'user')
    sender_id = data.get('sender_id')
    content = data.get('content', '')
    message_type = data.get('message_type', 'text')
    parent_message_id = data.get('parent_message_id')

    if not all([conversation_id, sender_id, content]):
        emit('error', {'message': 'Missing required fields'})
        return

    # Save message via service
    result, error = message_service.send_message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        parent_message_id=parent_message_id
    )

    if error:
        emit('error', {'message': error})
        return

    # Broadcast message to room
    emit('new_message', result, room=conversation_id)

    # If message is from a user, trigger agent responses
    if sender_type == 'user':
        # In a single-agent chat, we need the agent_id from the conversation participants
        from app.repositories.conversation_repo import conversation_repo
        participants = conversation_repo.get_conversation_participants(conversation_id)
        agent_participants = [p for p in participants if p.participant_type == 'agent']

        if agent_participants:
            emit('agent_typing', {
                'conversation_id': conversation_id,
                'agents': [{'agent_id': p.participant_id} for p in agent_participants]
            }, room=conversation_id)

            # Dispatch to orchestrator (runs agents in background)
            orchestrator_service.dispatch_to_agents(conversation_id, result['id'])


@socketio.on('agent_typing')
def handle_agent_typing(data):
    """Broadcast agent typing indicator."""
    conversation_id = data.get('conversation_id')
    agent_id = data.get('agent_id')
    is_typing = data.get('is_typing', True)

    emit('agent_typing_status', {
        'agent_id': agent_id,
        'is_typing': is_typing
    }, room=conversation_id)
