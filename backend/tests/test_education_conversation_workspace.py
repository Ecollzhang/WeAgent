from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def _seed_user(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(
            User(
                id="education-owner",
                username="education-owner",
                email="education-owner@example.com",
                password_hash="hash",
            )
        )
        db.session.add_all(
            [
                Workspace(
                    id="education-teacher-workspace",
                    user_id="education-owner",
                    domain="edu",
                    sub_role="teacher",
                    name="教师教育空间",
                ),
                Workspace(
                    id="research-workspace",
                    user_id="education-owner",
                    domain="rd",
                    name="研发空间",
                ),
            ]
        )
        db.session.commit()


def test_education_conversation_resolves_owned_role_workspace():
    app = create_app("testing")
    _seed_user(app)
    client = app.test_client()

    response = client.post(
        "/api/conversations",
        headers=_headers(app, "education-owner"),
        json={
            "title": "根据当前教案生成 PPT",
            "type": "group",
            "participant_ids": [],
            "kb_domain": "edu",
            "workspace_context": {"domain": "edu", "role": "teacher"},
        },
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["workspace_id"] == (
        "education-teacher-workspace"
    )

    with app.app_context():
        stored = Conversation.query.get(response.get_json()["data"]["id"])
        assert stored.workspace_id == "education-teacher-workspace"
        db.session.remove()
        db.drop_all()


def test_education_conversation_creates_missing_role_workspace():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(
            User(
                id="new-education-owner",
                username="new-education-owner",
                email="new-education-owner@example.com",
                password_hash="hash",
            )
        )
        db.session.commit()

    response = app.test_client().post(
        "/api/conversations",
        headers=_headers(app, "new-education-owner"),
        json={
            "title": "根据当前教案生成 PPT",
            "type": "group",
            "participant_ids": [],
            "kb_domain": "edu",
            "workspace_context": {"domain": "edu", "role": "teacher"},
        },
    )

    assert response.status_code == 201
    with app.app_context():
        workspace = Workspace.query.filter_by(
            user_id="new-education-owner",
            domain="edu",
            sub_role="teacher",
        ).one()
        assert response.get_json()["data"]["workspace_id"] == workspace.id
        db.session.remove()
        db.drop_all()


def test_hidden_execution_context_is_dispatched_but_not_saved_as_user_content(
    monkeypatch,
):
    app = create_app("testing")
    _seed_user(app)
    captured = {}

    class ImmediateThread:
        def __init__(self, target, args, daemon):
            captured["target"] = target
            captured["args"] = args
            captured["daemon"] = daemon

        def start(self):
            return None

    monkeypatch.setattr(
        "app.services.message_service.threading.Thread",
        ImmediateThread,
    )

    with app.app_context():
        conversation = Conversation(
            id="education-chat",
            title="课件制作",
            type="group",
            owner_id="education-owner",
            workspace_id="education-teacher-workspace",
            kb_domain="edu",
        )
        db.session.add(conversation)
        db.session.flush()
        db.session.add_all(
            [
                ConversationParticipant(
                    conversation_id=conversation.id,
                    participant_type="user",
                    participant_id="education-owner",
                ),
                ConversationParticipant(
                    conversation_id=conversation.id,
                    participant_type="agent",
                    participant_id="courseware-maker",
                    participant_name="课件制作师",
                ),
            ]
        )
        db.session.commit()

    response = app.test_client().post(
        "/api/messages",
        headers=_headers(app, "education-owner"),
        json={
            "conversation_id": "education-chat",
            "content": "根据当前教案生成 PPT。",
            "execution_context": "INTERNAL TOOL AND SCHEMA CONTRACT",
        },
    )

    assert response.status_code == 201
    with app.app_context():
        stored = Message.query.filter_by(
            conversation_id="education-chat",
            sender_type="user",
        ).one()
        assert stored.content == "根据当前教案生成 PPT。"
        assert "INTERNAL" not in stored.content
        db.session.remove()
        db.drop_all()
    assert captured["args"][2] == "INTERNAL TOOL AND SCHEMA CONTRACT"
