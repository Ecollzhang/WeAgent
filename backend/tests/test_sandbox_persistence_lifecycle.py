import io
import os
import tempfile
import zipfile
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message
from app.models.user import User
from app.services.conversation_service import conversation_service
from app.utils.timezone import beijing_now


def _workspace_zip():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("workspace/agents/writer/final.html", "<h1>durable</h1>")
    return stream.getvalue()


class FakeManager:
    def __init__(self):
        self.session = SimpleNamespace(
            session_id="conversation-1",
            container_id="container-1",
            host_port=50123,
            _check_alive=lambda: True,
        )
        self.destroyed = []
        self.restored = []
        self.runtime_auth_updates = []

    def get_session(self, session_id):
        return self.session

    def export_zip(self, session_id, path):
        assert session_id == "conversation-1"
        assert path == "/workspace"
        return _workspace_zip(), "application/zip", "attachment"

    def restore_zip(self, session_id, archive_bytes):
        self.restored.append((session_id, archive_bytes))
        return {"status": "ok", "restored_files": 1}

    def destroy_session(self, session_id):
        self.destroyed.append(session_id)
        self.session = None

    def update_runtime_auth(self, session_id, authorization):
        self.runtime_auth_updates.append((session_id, authorization))
        return {"status": "ok"}


@pytest.fixture()
def lifecycle_app():
    app = create_app("testing")
    temp = tempfile.TemporaryDirectory()
    app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=temp.name,
        SANDBOX_TTL_SECONDS=3600,
        SANDBOX_SNAPSHOT_MAX_BYTES=1024 * 1024,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            id="user-1",
            username="teacher",
            email="teacher@example.com",
            password_hash="x",
        )
        agent = Agent(
            id="agent-1",
            name="Writer",
            system_prompt="write",
            adapter_name="codex",
        )
        conversation = Conversation(
            id="conversation-1",
            owner_id=user.id,
            title="Durable education chat",
            kb_domain="edu",
            sandbox_server_fallback=True,
            sandbox_agent_adapters={"agent-1": "codex"},
            sandbox_session_id="conversation-1",
            sandbox_status="running",
            sandbox_generation=1,
            sandbox_expires_at=beijing_now() + timedelta(hours=1),
        )
        participant = ConversationParticipant(
            conversation_id=conversation.id,
            participant_type="agent",
            participant_id=agent.id,
            participant_name=agent.name,
        )
        message = Message(
            id="message-1",
            conversation_id=conversation.id,
            sender_type="agent",
            sender_id=agent.id,
            content="persist me",
            message_type="text",
            status="done",
        )
        db.session.add_all([user, agent, conversation, participant, message])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()
    temp.cleanup()


def test_snapshot_is_outside_docker_and_records_integrity(lifecycle_app):
    with lifecycle_app.app_context():
        conversation = Conversation.query.get("conversation-1")
        result = conversation_service.snapshot_sandbox(
            conversation,
            manager=FakeManager(),
        )
        db.session.refresh(conversation)

        assert result["status"] == "snapshotted"
        assert conversation.sandbox_snapshot_sha256
        assert conversation.sandbox_snapshot_size > 0
        assert conversation.sandbox_snapshot_at is not None
        assert not os.path.isabs(conversation.sandbox_snapshot_path)
        absolute = os.path.join(
            lifecycle_app.config["UPLOAD_FOLDER"],
            conversation.sandbox_snapshot_path,
        )
        assert os.path.isfile(absolute)
        assert open(absolute, "rb").read() == _workspace_zip()


def test_expired_runtime_is_snapshotted_and_stopped_without_deleting_chat(
    lifecycle_app,
):
    manager = FakeManager()
    with lifecycle_app.app_context():
        conversation = Conversation.query.get("conversation-1")
        conversation.sandbox_expires_at = beijing_now() - timedelta(seconds=1)
        db.session.commit()

        result = conversation_service.expire_idle_sandboxes(
            now=beijing_now(),
            manager=manager,
        )
        db.session.expire_all()

        conversation = Conversation.query.get("conversation-1")
        assert result["stopped"] == 1
        assert conversation.sandbox_status == "stopped"
        assert conversation.sandbox_snapshot_path
        assert Message.query.get("message-1").content == "persist me"
        assert manager.destroyed == ["conversation-1"]


def test_stopped_runtime_rehydrates_snapshot_as_a_new_generation(lifecycle_app):
    manager = FakeManager()
    captured = {}
    with lifecycle_app.app_context():
        conversation = Conversation.query.get("conversation-1")
        conversation_service.snapshot_sandbox(conversation, manager=manager)
        conversation.sandbox_status = "stopped"
        conversation.stopped_at = beijing_now()
        manager.session = None
        db.session.commit()

        def fake_create(target, participants, user_id, **kwargs):
            captured.update(kwargs)
            manager.session = SimpleNamespace(
                session_id=target.id,
                container_id="container-2",
                host_port=50124,
                _check_alive=lambda: True,
            )
            target.sandbox_session_id = target.id
            target.sandbox_container_id = "container-2"
            target.sandbox_host_port = 50124
            target.sandbox_status = "running"
            db.session.commit()
            return None

        with patch.object(
            conversation_service,
            "_create_agent_sandbox",
            side_effect=fake_create,
        ):
            result, error = conversation_service.ensure_sandbox_runtime(
                conversation,
                user_id="user-1",
                manager=manager,
            )

        db.session.refresh(conversation)
        assert error is None
        assert result["rehydrated"] is True
        assert result["runtime_generation"] == 2
        assert conversation.sandbox_generation == 2
        assert conversation.sandbox_status == "running"
        assert conversation.stopped_at is None
        assert manager.restored[0][0] == "conversation-1"
        assert manager.restored[0][1] == _workspace_zip()
        assert captured == {
            "kb_domain": "edu",
            "agent_configs": {"agent-1": {"adapter_name": "codex"}},
            "allow_server_fallback": True,
            "rehydrating": True,
        }


def test_live_runtime_refreshes_user_authorization_from_current_request(
    lifecycle_app,
):
    manager = FakeManager()
    with lifecycle_app.test_request_context(
        headers={"Authorization": "Bearer fresh-token"},
    ):
        conversation = Conversation.query.get("conversation-1")
        result, error = conversation_service.ensure_sandbox_runtime(
            conversation,
            user_id="user-1",
            manager=manager,
        )

    assert error is None
    assert result["rehydrated"] is False
    assert manager.runtime_auth_updates == [
        ("conversation-1", "Bearer fresh-token"),
    ]
