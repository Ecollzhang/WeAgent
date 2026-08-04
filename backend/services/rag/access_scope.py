"""Server-issued authorization scope for RAG search."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SearchScope:
    user_id: str
    domain: str
    workspace_id: str | None
    internal: bool
    education_role: str | None = None


def resolve_search_scope(
    *,
    internal: bool,
    headers: Mapping[str, str],
    payload: dict,
    jwt_identity: str | None = None,
) -> SearchScope:
    requested_domain = str(payload.get("domain") or "").strip()
    requested_workspace = str(payload.get("workspace_id") or "").strip() or None

    if internal:
        user_id = str(headers.get("X-WeAgent-User-ID") or "").strip()
        domain = str(headers.get("X-WeAgent-Domain") or "").strip()
        workspace_id = (
            str(headers.get("X-WeAgent-Workspace-ID") or "").strip() or None
        )
        education_role = (
            str(headers.get("X-WeAgent-Education-Role") or "").strip() or None
        )
        if not user_id or not domain:
            raise PermissionError("Internal RAG requests require a server-issued scope")
        if domain == "edu" and (
            not workspace_id or education_role not in {"teacher", "student"}
        ):
            raise PermissionError(
                "Education RAG requests require a course and membership role"
            )
        if requested_domain and requested_domain != domain:
            raise PermissionError("Requested domain is outside the authorized scope")
        if requested_workspace and requested_workspace != workspace_id:
            raise PermissionError("Requested workspace is outside the authorized scope")
        return SearchScope(
            user_id,
            domain,
            workspace_id,
            True,
            education_role=education_role,
        )

    user_id = str(jwt_identity or "").strip()
    if not user_id:
        raise PermissionError("Authenticated user scope is required")
    return SearchScope(
        user_id=user_id,
        domain=requested_domain or "rd",
        workspace_id=requested_workspace,
        internal=False,
    )


def document_allowed(document, scope: SearchScope) -> bool:
    """Apply the durable document boundary after vector retrieval.

    Education uses ``workspace_id`` as the course identifier.  Teachers can
    retrieve all active resources in their course; students can retrieve only
    resources explicitly published to the course.
    """
    if not document or document.domain != scope.domain:
        return False
    if scope.internal and scope.workspace_id:
        if document.workspace_id != scope.workspace_id:
            return False
        if scope.domain == "edu" and scope.education_role == "student":
            metadata = document.extra_meta if isinstance(document.extra_meta, dict) else {}
            return metadata.get("visibility_scope") == "course_published"
        return True
    return document.user_id == scope.user_id
