"""Bridge durable Education resources into the independently deployed RAG service."""

from __future__ import annotations

import requests
from flask import current_app

from .asset_models import EducationAsset


def _response_error(response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return str(
        payload.get("message")
        or payload.get("error")
        or f"RAG service returned HTTP {response.status_code}"
    )[:500]


def _rag_headers(resource, internal_key: str) -> dict:
    return {
        "X-Internal-API-Key": internal_key,
        "X-WeAgent-User-ID": str(resource.owner_user_id),
        "X-WeAgent-Domain": "edu",
        "X-WeAgent-Workspace-ID": str(resource.course_id),
        "X-WeAgent-Education-Role": "teacher",
        "X-WeAgent-Visibility": str(resource.visibility_scope),
        "X-WeAgent-Resource-ID": str(resource.id),
    }


def ingest_knowledge_resource(resource, *, app=None) -> bool:
    """Submit one committed Education asset to the course-scoped RAG index.

    Education remains the durable source of truth.  A RAG outage updates only
    the ingestion state and never deletes or rolls back the uploaded asset.
    """
    application = app or current_app
    if not application.config.get("EDUCATION_RAG_INGESTION_ENABLED", False):
        return False

    asset = getattr(resource, "asset", None)
    if asset is None:
        asset = EducationAsset.query.filter_by(id=resource.asset_id).first()
    if not asset or not asset.blob_bytes:
        resource.ingestion_status = "failed"
        resource.ingestion_error = "durable Education asset is unavailable"
        return False

    base_url = str(
        application.config.get("RAG_SERVICE_URL", "http://127.0.0.1:5104")
    ).rstrip("/")
    internal_key = str(
        application.config.get("RAG_INTERNAL_API_KEY", "")
    ).strip()
    if not internal_key:
        resource.ingestion_status = "failed"
        resource.ingestion_error = "RAG internal service credential is unavailable"
        return False

    headers = _rag_headers(resource, internal_key)
    try:
        uploaded = requests.post(
            f"{base_url}/api/rag/documents/upload",
            headers=headers,
            files={
                "file": (
                    asset.original_filename,
                    bytes(asset.blob_bytes),
                    asset.media_type,
                )
            },
            timeout=(3, 60),
        )
        if uploaded.status_code != 201:
            raise RuntimeError(_response_error(uploaded))
        payload = uploaded.json()
        document = payload.get("data") if isinstance(payload, dict) else None
        document_id = str(
            (document or {}).get("id") if isinstance(document, dict) else ""
        ).strip()
        if not document_id:
            raise RuntimeError("RAG upload did not return a document id")
        confirmed = requests.post(
            f"{base_url}/api/rag/documents/{document_id}/confirm",
            headers=headers,
            timeout=(3, 30),
        )
        if confirmed.status_code not in {200, 202}:
            raise RuntimeError(_response_error(confirmed))
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        resource.ingestion_status = "failed"
        resource.ingestion_error = str(exc)[:500]
        return False

    metadata = dict(resource.metadata_json or {})
    metadata["rag_document_id"] = document_id
    resource.metadata_json = metadata
    resource.ingestion_status = "processing"
    resource.ingestion_error = None
    return True


def refresh_knowledge_resource_status(resource, *, app=None) -> bool:
    """Refresh an accepted ingestion without making RAG the source of truth."""
    application = app or current_app
    if resource.ingestion_status != "processing":
        return False
    document_id = str(
        (resource.metadata_json or {}).get("rag_document_id") or ""
    ).strip()
    internal_key = str(
        application.config.get("RAG_INTERNAL_API_KEY", "")
    ).strip()
    if not document_id or not internal_key:
        return False
    base_url = str(
        application.config.get("RAG_SERVICE_URL", "http://127.0.0.1:5104")
    ).rstrip("/")
    try:
        response = requests.get(
            f"{base_url}/api/rag/documents/{document_id}",
            headers=_rag_headers(resource, internal_key),
            timeout=(2, 8),
        )
        if response.status_code != 200:
            return False
        payload = response.json()
        document = payload.get("data") if isinstance(payload, dict) else None
        status = (
            str((document or {}).get("status") or "")
            if isinstance(document, dict)
            else ""
        )
    except (requests.RequestException, ValueError):
        return False
    if status == "ready":
        resource.ingestion_status = "ready"
        resource.ingestion_error = None
        return True
    if status == "error":
        resource.ingestion_status = "failed"
        resource.ingestion_error = str(
            ((document or {}).get("extra_meta") or {}).get("error")
            or "RAG indexing failed"
        )[:500]
        return True
    return False
