"""Response-only projection for provider output shown in chat.

The original provider stream remains persisted for diagnostics.  This module
removes transport preambles and private tool traces from the user-facing API
and websocket payloads.
"""

import re


_CONTROLLED_FILE_BLOCK = re.compile(
    r"^##[ \t]+/?workspace/[^\r\n]+\r?\n"
    r"```[^\r\n]*\r?\n.*?^```[ \t]*(?:\r?\n|$)",
    flags=re.MULTILINE | re.DOTALL,
)
_TOOL_TRACE = re.compile(
    r"<tool_call\b[^>]*>.*?(?:</tool_call>|</[^>\r\n]*DSML[^>]*>|$)",
    flags=re.DOTALL | re.IGNORECASE,
)
_PRIVATE_PLANNING_LINE = re.compile(
    r"^(?:This will\b|I (?:will|need|should)\b|Let me\b|"
    r"我将先(?:探测|读取|检查)|接下来(?:我)?(?:会|将))",
    flags=re.IGNORECASE,
)


def public_agent_output(raw_output):
    """Return safe display text without mutating the persisted audit trace."""
    text = str(raw_output or "")
    had_private_trace = bool(_TOOL_TRACE.search(text))
    text = _CONTROLLED_FILE_BLOCK.sub("", text)
    text = re.sub(
        r"Reading additional input from stdin\.\.\.\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = _TOOL_TRACE.sub("", text)
    if had_private_trace:
        text = "\n".join(
            line
            for line in text.splitlines()
            if not _PRIVATE_PLANNING_LINE.match(line.strip())
        )
    # Canonical identifiers are projected through trusted cards and routes.
    # Free-form model text must not expose database, workspace or conversation
    # UUIDs that happened to be present in the hidden service context.
    text = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
        r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        "[内部标识已隐藏]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bedu-intent-[A-Za-z0-9_.-]+\b",
        "前置步骤",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text
