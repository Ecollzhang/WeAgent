from app import create_app, db
from app.models.artifact import Artifact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.sandbox.host.manager import DockerContainerManager
from app.services.message_service import _message_dict


def test_manager_keeps_chain_and_delegate_result_shapes_without_drafts():
    class FakeClient:
        def __init__(self):
            self.chain_result = [
                {
                    "status": "ok",
                    "agent_id": "planner",
                    "reply": "plan ready",
                    "tool_results": [{"path": "plan.md"}],
                },
                {
                    "status": "ok",
                    "agent_id": "builder",
                    "reply": "build ready",
                },
            ]
            self.delegate_result = {
                "status": "ok",
                "moderator_id": "moderator",
                "results": [
                    {
                        "status": "ok",
                        "agent_id": "builder",
                        "reply": "delegated work done",
                    }
                ],
            }

        def send_chain(self, _messages):
            return self.chain_result

        def delegate(self, _message, _moderator_id, _target_agent_ids):
            return self.delegate_result

    class FakeSession:
        session_id = "session-regression"
        client = FakeClient()

    manager = DockerContainerManager()
    manager._sessions["session-regression"] = FakeSession()
    manager.recover_sessions = lambda: None

    chain = manager.send_chain(
        "session-regression",
        [{"agent_id": "planner", "message": "plan"}],
    )
    delegate = manager.delegate_message(
        "session-regression",
        "delegate",
        moderator_id="moderator",
        target_agent_ids=["builder"],
    )

    assert chain == manager._sessions["session-regression"].client.chain_result
    assert chain[0]["tool_results"][0]["path"] == "plan.md"
    assert delegate == manager._sessions["session-regression"].client.delegate_result
    assert delegate["results"][0]["agent_id"] == "builder"
    assert "skill_drafts_sync" not in delegate


def test_message_dict_preserves_artifact_summary_and_progress_elements():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            id="user-regression",
            username="regression",
            email="regression@example.com",
            password_hash="hash",
        )
        conversation = Conversation(
            id="conversation-regression",
            title="Regression",
            type="group",
            owner_id=user.id,
            sandbox_session_id="session-regression",
            sandbox_status="running",
        )
        artifact = Artifact(
            id="artifact-regression",
            artifact_type="code",
            title="Result.py",
            content="print('ok')",
            language="python",
        )
        db.session.add_all([user, conversation, artifact])
        db.session.flush()

        message = Message(
            id="message-regression",
            conversation_id=conversation.id,
            sender_type="agent",
            sender_id="builder",
            content="Working",
            elements=[
                {
                    "type": "progress",
                    "content": "Building artifact",
                    "status": "running",
                }
            ],
            artifact_id=artifact.id,
        )
        db.session.add(message)
        db.session.commit()

        data = _message_dict(message)

        assert data["artifact"] == {
            "id": artifact.id,
            "artifact_type": "code",
            "title": "Result.py",
            "language": "python",
        }
        assert data["elements"][0]["type"] == "progress"
        assert data["elements"][0]["content"] == "Building artifact"
        db.session.remove()
        db.drop_all()
