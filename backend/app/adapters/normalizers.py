from app.adapters.types import make_event


def normalize_codex_event(raw, request):
    raw_type = raw.get("type")

    if raw_type in ("message_delta", "delta"):
        return [_message_delta(request, raw.get("delta") or raw.get("content") or raw.get("text", ""))]

    if raw_type in ("message_completed", "agent_message", "final_answer"):
        return [_message_completed(request, raw.get("content") or raw.get("message") or raw.get("text", ""))]

    if raw_type == "tool_call":
        return [
            make_event(
                "tool.started",
                request,
                toolName=raw.get("name") or raw.get("tool_name"),
                input=raw.get("input"),
            )
        ]

    if raw_type == "tool_result":
        return [
            make_event(
                "tool.completed",
                request,
                toolName=raw.get("name") or raw.get("tool_name"),
                output=raw.get("output"),
            )
        ]

    if raw_type in ("artifact", "file_created"):
        return [_artifact_created(request, raw)]

    if raw_type == "error":
        return [_agent_failed(request, raw.get("message") or raw.get("error") or "Codex adapter failed")]

    return []


def normalize_claude_event(raw, request):
    raw_type = raw.get("type")

    if raw_type == "content_block_delta":
        delta = raw.get("delta") or {}
        return [_message_delta(request, delta.get("text") or raw.get("text", ""))]

    if raw_type == "assistant":
        text = _claude_message_text(raw.get("message") or raw)
        return [_message_delta(request, text)] if text else []

    if raw_type == "result":
        return [_message_completed(request, raw.get("result") or raw.get("content") or "")]

    if raw_type == "content_block_start":
        block = raw.get("content_block") or {}
        if block.get("type") == "tool_use":
            return [
                make_event(
                    "tool.started",
                    request,
                    toolName=block.get("name"),
                    input=block.get("input"),
                )
            ]

    if raw_type == "content_block_stop":
        block = raw.get("content_block") or {}
        if block.get("type") == "tool_result":
            return [
                make_event(
                    "tool.completed",
                    request,
                    toolName=block.get("name"),
                    output=block.get("content"),
                )
            ]

    if raw_type == "artifact":
        return [_artifact_created(request, raw)]

    if raw_type == "error":
        error = raw.get("error")
        if isinstance(error, dict):
            error = error.get("message")
        return [_agent_failed(request, error or "Claude adapter failed")]

    return []


def _message_delta(request, content):
    return make_event("message.delta", request, content=content, text=content)


def _message_completed(request, content):
    return make_event("message.completed", request, content=content, finalText=content)


def _agent_failed(request, error):
    return make_event("agent.failed", request, error=str(error))


def _artifact_created(request, raw):
    path = raw.get("path") or raw.get("storagePath")
    title = raw.get("title") or path or "Artifact"
    artifact = {
        "id": raw.get("id") or path or title,
        "type": raw.get("artifactType") or raw.get("artifact_type") or "file",
        "title": title,
        "storagePath": path,
    }
    return make_event("artifact.created", request, artifact=artifact)


def _claude_message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    return "".join(parts)
