from app import create_app, db
from app.models.conversation import Conversation
from app.models.user import User
from app.models.workspace import Workspace
from app.services.conversation_service import _trusted_rag_scope


def test_rag_scope_is_issued_from_conversation_owner_and_workspace():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(
            id="scope-owner",
            username="scope-owner",
            email="scope-owner@example.com",
            password_hash="hash",
        )
        workspace = Workspace(
            id="scope-workspace",
            user_id=owner.id,
            domain="edu",
            name="Education",
        )
        conversation = Conversation(
            id="scope-conversation",
            title="Scoped",
            type="single",
            owner_id=owner.id,
            workspace_id=workspace.id,
        )
        db.session.add_all([owner, workspace, conversation])
        db.session.commit()

        assert _trusted_rag_scope(conversation, owner.id, "rd") == {
            "RAG_SCOPE_USER_ID": owner.id,
            "RAG_SCOPE_DOMAIN": "edu",
            "RAG_SCOPE_WORKSPACE_ID": workspace.id,
        }
        db.session.remove()
        db.drop_all()


def test_rag_scope_without_workspace_accepts_only_known_domain():
    conversation = type("ConversationStub", (), {"workspace_id": None})()

    assert _trusted_rag_scope(conversation, "user-1", "edu") == {
        "RAG_SCOPE_USER_ID": "user-1",
        "RAG_SCOPE_DOMAIN": "edu",
    }
    assert _trusted_rag_scope(conversation, "user-1", "all") == {
        "RAG_SCOPE_USER_ID": "user-1",
        "RAG_SCOPE_DOMAIN": "rd",
    }


def test_education_rag_scope_uses_bound_course_not_core_workspace():
    conversation = type(
        "ConversationStub",
        (),
        {"workspace_id": "generic-education-workspace"},
    )()

    assert _trusted_rag_scope(
        conversation,
        "teacher-1",
        "edu",
        education_context={
            "course_id": "course-allowed",
            "membership_role": "teacher",
        },
    ) == {
        "RAG_SCOPE_USER_ID": "teacher-1",
        "RAG_SCOPE_DOMAIN": "edu",
        "RAG_SCOPE_WORKSPACE_ID": "course-allowed",
        "RAG_SCOPE_EDUCATION_ROLE": "teacher",
    }
