from flask import Blueprint, request, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from app.utils.response import success_response, error_response
from app.schemas.message_schema import SendMessageSchema
from app.services.message_service import message_service
from marshmallow import INCLUDE, ValidationError
import json
import queue

message_bp = Blueprint('messages', __name__)


def _format_sse(data, event_name=None):
    payload = json.dumps(data, ensure_ascii=False)
    if event_name:
        return f'event: {event_name}\ndata: {payload}\n\n'
    return f'data: {payload}\n\n'


def _is_agent_event(data):
    return data.get('schemaVersion') == 'v1' and data.get('type')


@message_bp.route('', methods=['POST'])
@jwt_required()
def send_message():
    """Send a message in a conversation."""
    user_id = get_jwt_identity()

    try:
        schema = SendMessageSchema()
        data = schema.load(request.get_json(silent=True) or {}, unknown=INCLUDE)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = message_service.send_message(
        conversation_id=data['conversation_id'],
        sender_type='user',
        sender_id=user_id,
        content=data['content'],
        message_type=data.get('message_type', 'text'),
        parent_message_id=data.get('parent_message_id'),
        artifact_id=data.get('artifact_id'),
        target_agent_ids=data.get('target_agent_ids') or [],
        agent_configs=data.get('agent_configs') or {},
    )

    if error:
        return error_response(error, code=400)

    return success_response(result, message='Message sent', code=201)


@message_bp.route('/conversation/<conversation_id>', methods=['GET'])
@jwt_required()
def get_messages(conversation_id):
    """Get messages for a conversation."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    result, error = message_service.get_conversation_messages(
        conversation_id, page=page, per_page=per_page
    )

    if error:
        return error_response(error, code=404)

    return success_response(result)


@message_bp.route('/<message_id>/pin', methods=['POST'])
@jwt_required()
def toggle_pin(message_id):
    """Toggle pin status of a message."""
    result, error = message_service.toggle_pin(message_id)

    if error:
        return error_response(error, code=404)

    return success_response(result, message='Pin status toggled')


@message_bp.route('/conversation/<conversation_id>/pinned', methods=['GET'])
@jwt_required()
def get_pinned(conversation_id):
    """Get pinned messages for a conversation."""
    result, error = message_service.get_pinned_messages(conversation_id)

    if error:
        return error_response(error, code=400)

    return success_response(result)


@message_bp.route('/poll/<conversation_id>', methods=['GET'])
@jwt_required()
def poll_messages(conversation_id):
    """Poll for new messages in a conversation since a given message ID.

    Query params:
        after (str, optional): message ID — only return messages newer than this.
    """
    after = request.args.get('after')
    result, error = message_service.poll_messages(conversation_id, after=after)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@message_bp.route('/stream/<conversation_id>', methods=['GET'])
def stream_messages(conversation_id):
    """SSE endpoint — true long connection with real-time event streaming.

    Uses query-param auth (token) since EventSource cannot set headers.
    Phase 1: catch-up — sends existing messages from DB (after reference ID).
    Phase 2: real-time — subscribes to in-memory queue, blocks until data arrives.

    Query params:
        token (str): JWT token (required)
        after (str, optional): message ID — only return messages newer than this.
    """
    token = request.args.get('token')
    if not token:
        return error_response('Missing token', code=401)

    try:
        decode_token(token)
    except Exception:
        return error_response('Invalid token', code=401)

    after = request.args.get('after')

    from app.services.message_service import subscribe, unsubscribe

    def generate():
        last_after = after

        # Phase 1: catch-up — send any messages already in DB
        result, error = message_service.poll_messages(conversation_id, after=last_after)
        if not error and result and result.get('items'):
            for msg in result['items']:
                yield _format_sse(msg)
                last_after = msg['id']

        # Phase 2: real-time — subscribe to in-memory queue (true event-driven)
        q = subscribe(conversation_id)
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    # Skip internal control signals
                    if msg.get('_type') == 'agent_done':
                        yield _format_sse({"reason": "complete"}, "done")
                        return
                    # Agent events use named SSE events; persisted messages stay default data events.
                    if _is_agent_event(msg):
                        yield _format_sse(msg, msg['type'])
                    else:
                        yield _format_sse(msg)
                    last_after = msg.get('id', last_after)
                except queue.Empty:
                    yield _format_sse({"reason": "timeout"}, "done")
                    return
        finally:
            unsubscribe(conversation_id, q)

    response = Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
    )
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
