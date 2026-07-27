from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.conversation import Conversation, ConversationParticipant
from app.models.user import User
from app.sandbox.api import routes


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


class FileManagerProbe:
    def __init__(self):
        self.calls = []

    def get_file_tree(self, session_id, **kwargs):
        self.calls.append(("tree", session_id))
        return {"tree": {"path": "/workspace", "children": []}}

    def __getattr__(self, name):
        def unexpected(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            raise AssertionError(f"unauthorized request reached manager: {name}")

        return unexpected


def test_sandbox_file_routes_require_conversation_membership():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(
            id="sandbox-owner",
            username="sandbox-owner",
            email="sandbox-owner@example.com",
            password_hash="hash",
        )
        participant = User(
            id="sandbox-participant",
            username="sandbox-participant",
            email="sandbox-participant@example.com",
            password_hash="hash",
        )
        outsider = User(
            id="sandbox-outsider",
            username="sandbox-outsider",
            email="sandbox-outsider@example.com",
            password_hash="hash",
        )
        conversation = Conversation(
            id="sandbox-conversation",
            title="Private Education workspace",
            type="group",
            owner_id=owner.id,
            sandbox_session_id="private-sandbox-session",
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
        db.session.commit()

    previous_manager = routes._manager
    probe = FileManagerProbe()
    routes._manager = probe
    try:
        client = app.test_client()
        outsider_headers = _headers(app, "sandbox-outsider")
        cases = [
            ("get", "/api/sandbox/sessions/private-sandbox-session/agents/a/files?path=x"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/agents/a/files/raw?path=x"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/files/tree"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/files/raw?path=x"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/files/download?path=x"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/files/export-zip"),
            ("get", "/api/sandbox/sessions/private-sandbox-session/workspace/index.html"),
            ("put", "/api/sandbox/sessions/private-sandbox-session/files/write"),
        ]
        for method, url in cases:
            response = getattr(client, method)(
                url,
                headers=outsider_headers,
                json={"path": "/workspace/x", "content": "x"} if method == "put" else None,
            )
            assert response.status_code == 404, url
        assert probe.calls == []

        allowed = client.get(
            "/api/sandbox/sessions/private-sandbox-session/files/tree",
            headers=_headers(app, "sandbox-participant"),
        )
        assert allowed.status_code == 200
        assert probe.calls == [("tree", "private-sandbox-session")]
    finally:
        routes._manager = previous_manager
        with app.app_context():
            db.session.remove()
            db.drop_all()
