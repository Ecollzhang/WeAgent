"""Server-issued authorization scope for RAG search."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SearchScope:
    user_id: str
    domain: str
    workspace_id: str | None
    internal: bool


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
        if not user_id or not domain:
            raise PermissionError("Internal RAG requests require a server-issued scope")
        if requested_domain and requested_domain != domain:
            raise PermissionError("Requested domain is outside the authorized scope")
        if requested_workspace and requested_workspace != workspace_id:
            raise PermissionError("Requested workspace is outside the authorized scope")
        return SearchScope(user_id, domain, workspace_id, True)

    user_id = str(jwt_identity or "").strip()
    if not user_id:
        raise PermissionError("Authenticated user scope is required")
    return SearchScope(
        user_id=user_id,
        domain=requested_domain or "rd",
        workspace_id=requested_workspace,
        internal=False,
    )
