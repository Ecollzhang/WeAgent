from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message
from app.models.user import User


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def _token(app, user_id):
    with app.app_context():
        return create_access_token(identity=user_id)


def _seed_private_conversation(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(
            id="chat-owner",
            username="chat-owner",
            email="chat-owner@example.com",
            password_hash="hash",
        )
        participant = User(
            id="chat-participant",
            username="chat-participant",
            email="chat-participant@example.com",
            password_hash="hash",
        )
        outsider = User(
            id="chat-outsider",
            username="chat-outsider",
            email="chat-outsider@example.com",
            password_hash="hash",
        )
        conversation = Conversation(
            id="private-chat",
            title="Private Education planning",
            type="group",
            owner_id=owner.id,
        )
        db.session.add_all([owner, participant, outsider, conversation])
        db.session.flush()
        db.session.add_all(
            [
                ConversationParticipant(
                    conversation_id=conversation.id,
                    participant_type="user",
                    participant_id=owner.id,
                ),
                ConversationParticipant(
                    conversation_id=conversation.id,
                    participant_type="user",
                    participant_id=participant.id,
                ),
                Message(
                    id="private-message",
                    conversation_id=conversation.id,
                    sender_type="user",
                    sender_id=owner.id,
                    content="Private student evidence",
                    is_pinned=True,
                ),
            ]
        )
        db.session.commit()


def test_conversation_and_message_reads_require_membership():
    app = create_app("testing")
    _seed_private_conversation(app)
    client = app.test_client()

    participant = _headers(app, "chat-participant")
    outsider = _headers(app, "chat-outsider")
    readable_paths = [
        "/api/conversations/private-chat",
        "/api/messages/conversation/private-chat",
        "/api/messages/poll/private-chat",
        "/api/messages/conversation/private-chat/pinned",
    ]
    for path in readable_paths:
        assert client.get(path, headers=participant).status_code == 200, path
        response = client.get(path, headers=outsider)
        assert response.status_code == 404, path
        assert "Private student evidence" not in response.get_data(as_text=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_message_writes_and_sse_require_membership():
    app = create_app("testing")
    _seed_private_conversation(app)
    client = app.test_client()
    participant = _headers(app, "chat-participant")
    outsider = _headers(app, "chat-outsider")

    allowed = client.post(
        "/api/messages",
        headers=participant,
        json={"conversation_id": "private-chat", "content": "Participant reply"},
    )
    assert allowed.status_code == 201

    denied_send = client.post(
        "/api/messages",
        headers=outsider,
        json={"conversation_id": "private-chat", "content": "Intrusion"},
    )
    assert denied_send.status_code == 404

    denied_pin = client.post(
        "/api/messages/private-message/pin",
        headers=outsider,
    )
    assert denied_pin.status_code == 404

    denied_stream = client.get(
        f"/api/messages/stream/private-chat?token={_token(app, 'chat-outsider')}"
    )
    assert denied_stream.status_code == 404
    assert "Private student evidence" not in denied_stream.get_data(as_text=True)

    with app.app_context():
        assert (
            Message.query.filter_by(
                conversation_id="private-chat",
                content="Intrusion",
            ).first()
            is None
        )
        db.session.remove()
        db.drop_all()
