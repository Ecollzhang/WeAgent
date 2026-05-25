from datetime import datetime, timezone


DEFAULT_MAX_MESSAGES = 20
_recorded_context = {}
message_repo = None


class ConversationContextService:
    """Builds WeAgent-owned context for one conversation."""

    def build_context(
        self,
        conversation_id,
        current_user_message_id=None,
        max_messages=DEFAULT_MAX_MESSAGES,
    ):
        messages = self._load_messages(conversation_id)
        transcript = [
            self._message_to_transcript_item(message)
            for message in self._bounded_messages(
                messages,
                current_user_message_id=current_user_message_id,
                max_messages=max_messages,
            )
        ]
        recorded = list(_recorded_context.get(str(conversation_id), []))
        artifact_context = self._artifact_context_from_messages(messages) + recorded

        return {
            "conversation_id": conversation_id,
            "transcript": transcript,
            "file_context": list(artifact_context),
            "artifact_context": artifact_context,
            "summary": self._build_summary(transcript, artifact_context),
            "limits": {"max_messages": max_messages},
        }

    def record_event(self, conversation_id, event):
        if event.get("type") != "artifact.created":
            return None

        artifact = event.get("artifact") or {}
        path = artifact.get("storagePath") or artifact.get("path")
        if not path:
            return None

        entry = {
            "kind": "artifact",
            "path": path,
            "title": artifact.get("title") or path,
            "source_event_type": event.get("type"),
            "agent_id": event.get("agentId"),
            "created_at": _utc_now_iso(),
        }
        _recorded_context.setdefault(str(conversation_id), []).append(entry)
        return entry

    def format_prompt(self, system_prompt, context, current_user_message):
        return "\n\n".join(
            [
                "## Agent Instructions\n" + (system_prompt or "Follow the user request."),
                "## Conversation Context\n" + self._format_transcript(context.get("transcript", [])),
                "## File and Artifact Context\n"
                + self._format_file_context(
                    context.get("file_context") or context.get("artifact_context") or []
                ),
                "## Current User Message\n" + (current_user_message or ""),
            ]
        )

    def _load_messages(self, conversation_id):
        repo = _get_message_repo()
        if not hasattr(repo, "get_all"):
            return []
        return list(repo.get_all(conversation_id=conversation_id))

    def _bounded_messages(self, messages, current_user_message_id, max_messages):
        filtered = [
            message
            for message in messages
            if not _is_current_user_message_duplicate(message, current_user_message_id)
        ]
        ordered = sorted(filtered, key=lambda message: getattr(message, "created_at", datetime.min))
        return ordered[-max_messages:]

    def _message_to_transcript_item(self, message):
        created_at = getattr(message, "created_at", None)
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        return {
            "sender_type": getattr(message, "sender_type", ""),
            "sender_id": getattr(message, "sender_id", ""),
            "content": getattr(message, "content", ""),
            "created_at": created_at,
        }

    def _artifact_context_from_messages(self, messages):
        entries = []
        for message in messages:
            artifact = getattr(message, "artifact", None)
            if not artifact:
                continue
            title = getattr(artifact, "title", None) or getattr(artifact, "id", None) or "Artifact"
            entries.append(
                {
                    "kind": "artifact",
                    "path": getattr(artifact, "preview_url", "") or getattr(artifact, "deploy_url", ""),
                    "title": title,
                    "source_event_type": "message.artifact",
                    "agent_id": getattr(message, "sender_id", None),
                    "created_at": _created_at_iso(message),
                }
            )
        return entries

    def _build_summary(self, transcript, artifact_context):
        parts = []
        if transcript:
            parts.append(f"{len(transcript)} recent messages")
        if artifact_context:
            parts.append(f"{len(artifact_context)} file/artifact references")
        return "; ".join(parts)

    def _format_transcript(self, transcript):
        if not transcript:
            return "No prior conversation context."
        lines = []
        for item in transcript:
            role = item.get("sender_type") or "unknown"
            sender_id = item.get("sender_id") or ""
            content = item.get("content") or ""
            lines.append(f"- {role} {sender_id}: {content}")
        return "\n".join(lines)

    def _format_file_context(self, file_context):
        if not file_context:
            return "No recorded file or artifact context."
        lines = []
        for item in file_context:
            title = item.get("title") or item.get("path") or "Artifact"
            path = item.get("path") or "(no path)"
            kind = item.get("kind") or "artifact"
            lines.append(f"- {kind}: {title} ({path})")
        return "\n".join(lines)


def _is_current_user_message_duplicate(message, current_user_message_id):
    return bool(current_user_message_id and getattr(message, "id", None) == current_user_message_id)


def _created_at_iso(message):
    created_at = getattr(message, "created_at", None)
    if isinstance(created_at, datetime):
        return created_at.isoformat()
    return created_at


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_message_repo():
    global message_repo
    if message_repo is not None:
        return message_repo
    try:
        from app.repositories.message_repo import message_repo as repo
    except Exception:
        return None
    message_repo = repo
    return message_repo


def clear_recorded_context():
    _recorded_context.clear()


conversation_context_service = ConversationContextService()
