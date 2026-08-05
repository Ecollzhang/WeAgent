from types import SimpleNamespace
from unittest.mock import patch

from services.edu.rag_ingestion import ingest_knowledge_resource


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_knowledge_resource_is_ingested_with_course_and_visibility_scope():
    resource = SimpleNamespace(
        id="resource-1",
        course_id="course-1",
        owner_user_id="teacher-1",
        visibility_scope="course_published",
        ingestion_status="pending",
        ingestion_error=None,
        metadata_json={},
        asset=SimpleNamespace(
            blob_bytes=b"%PDF-real-content",
            original_filename="reading.pdf",
            media_type="application/pdf",
        ),
    )
    app = SimpleNamespace(
        config={
            "EDUCATION_RAG_INGESTION_ENABLED": True,
            "RAG_SERVICE_URL": "http://rag:5104",
            "RAG_INTERNAL_API_KEY": "internal-secret",
        }
    )

    with patch(
        "services.edu.rag_ingestion.requests.post",
        side_effect=[
            _Response(201, {"data": {"id": "rag-document-1"}}),
            _Response(202, {"data": {"id": "rag-document-1", "status": "processing"}}),
        ],
    ) as post:
        assert ingest_knowledge_resource(resource, app=app) is True

    upload = post.call_args_list[0]
    assert upload.args[0] == "http://rag:5104/api/rag/documents/upload"
    assert upload.kwargs["headers"] == {
        "X-Internal-API-Key": "internal-secret",
        "X-WeAgent-User-ID": "teacher-1",
        "X-WeAgent-Domain": "edu",
        "X-WeAgent-Workspace-ID": "course-1",
        "X-WeAgent-Education-Role": "teacher",
        "X-WeAgent-Visibility": "course_published",
        "X-WeAgent-Resource-ID": "resource-1",
    }
    assert resource.ingestion_status == "processing"
    assert resource.metadata_json["rag_document_id"] == "rag-document-1"


def test_rag_failure_does_not_destroy_the_durable_education_resource():
    resource = SimpleNamespace(
        id="resource-1",
        course_id="course-1",
        owner_user_id="teacher-1",
        visibility_scope="course_teacher",
        ingestion_status="pending",
        ingestion_error=None,
        metadata_json={"source": "teacher_upload"},
        asset=SimpleNamespace(
            blob_bytes=b"document",
            original_filename="lesson.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )
    app = SimpleNamespace(
        config={
            "EDUCATION_RAG_INGESTION_ENABLED": True,
            "RAG_SERVICE_URL": "http://rag:5104",
            "RAG_INTERNAL_API_KEY": "internal-secret",
        }
    )

    with patch(
        "services.edu.rag_ingestion.requests.post",
        return_value=_Response(503, {"message": "unavailable"}),
    ):
        assert ingest_knowledge_resource(resource, app=app) is False

    assert resource.ingestion_status == "failed"
    assert "unavailable" in resource.ingestion_error
    assert resource.metadata_json == {"source": "teacher_upload"}
