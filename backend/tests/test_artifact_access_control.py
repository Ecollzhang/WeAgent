from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message
from app.models.user import User


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def test_artifact_reads_updates_and_message_lists_enforce_conversation_acl():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(
            id="artifact-owner",
            username="artifact-owner",
            email="artifact-owner@example.com",
            password_hash="hash",
        )
        participant = User(
            id="artifact-participant",
            username="artifact-participant",
            email="artifact-participant@example.com",
            password_hash="hash",
        )
        outsider = User(
            id="artifact-outsider",
            username="artifact-outsider",
            email="artifact-outsider@example.com",
            password_hash="hash",
        )
        conversation = Conversation(
            id="artifact-conversation",
            title="Private lesson planning",
            type="group",
            owner_id=owner.id,
        )
        db.session.add_all([owner, participant, outsider, conversation])
        db.session.flush()
        db.session.add(
            ConversationParticipant(
                conversation_id=conversation.id,
                participant_type="user",
                participant_id=participant.id,
            )
        )
        message = Message(
            id="artifact-message",
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=owner.id,
            content="Create a lesson plan",
        )
        db.session.add(message)
        db.session.commit()

    client = app.test_client()
    created = client.post(
        "/api/artifacts",
        headers=_headers(app, "artifact-owner"),
        json={
            "message_id": "artifact-message",
            "artifact_type": "document",
            "title": "Lesson plan",
            "content": "private draft",
        },
    )
    assert created.status_code == 201
    artifact_id = created.get_json()["data"]["id"]

    assert client.get(
        f"/api/artifacts/{artifact_id}",
        headers=_headers(app, "artifact-participant"),
    ).status_code == 200
    assert client.get(
        f"/api/artifacts/{artifact_id}",
        headers=_headers(app, "artifact-outsider"),
    ).status_code == 404
    assert client.put(
        f"/api/artifacts/{artifact_id}",
        headers=_headers(app, "artifact-outsider"),
        json={"content": "stolen"},
    ).status_code == 404
    assert client.get(
        "/api/artifacts/message/artifact-message",
        headers=_headers(app, "artifact-outsider"),
    ).status_code == 404

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_artifact_cannot_be_attached_to_an_unrelated_users_message():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(
            id="message-owner",
            username="message-owner",
            email="message-owner@example.com",
            password_hash="hash",
        )
        outsider = User(
            id="message-outsider",
            username="message-outsider",
            email="message-outsider@example.com",
            password_hash="hash",
        )
        conversation = Conversation(
            id="private-conversation",
            title="Private",
            type="single",
            owner_id=owner.id,
        )
        db.session.add_all([owner, outsider, conversation])
        db.session.flush()
        db.session.add(
            Message(
                id="private-message",
                conversation_id=conversation.id,
                sender_type="user",
                sender_id=owner.id,
                content="private",
            )
        )
        db.session.commit()

    response = app.test_client().post(
        "/api/artifacts",
        headers=_headers(app, "message-outsider"),
        json={
            "message_id": "private-message",
            "artifact_type": "document",
            "title": "Unauthorized",
        },
    )

    assert response.status_code == 404
    with app.app_context():
        db.session.remove()
        db.drop_all()
