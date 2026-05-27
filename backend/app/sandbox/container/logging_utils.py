"""
container.logging_utils - Lightweight sandbox logging helpers.

Logs are written to both container stdout and /workspace/.session/logs so
operators can inspect execution with docker logs or by browsing the workspace.
"""

import json
import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from typing import Any


LOG_DIR = "/workspace/.session/logs"
AGENT_LOG_DIR = os.path.join(LOG_DIR, "agents")
DEFAULT_MAX_TEXT = 500

_configured = False
_lock = threading.Lock()


def _ensure_dirs() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(AGENT_LOG_DIR, exist_ok=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def shorten(value: Any, limit: int = DEFAULT_MAX_TEXT) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + f"...<truncated {len(text) - limit} chars>"


def configure_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("weagent.sandbox")
    if _configured:
        return logger

    _ensure_dirs()
    level_name = os.environ.get("WEAGENT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "sandbox.log"),
        maxBytes=int(os.environ.get("WEAGENT_LOG_MAX_BYTES", "5242880")),
        backupCount=int(os.environ.get("WEAGENT_LOG_BACKUPS", "5")),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    _configured = True
    logger.info("logging_configured log_dir=%s level=%s", LOG_DIR, logging.getLevelName(level))
    return logger


def get_logger(name: str = "") -> logging.Logger:
    base = configure_logging()
    if not name:
        return base
    return logging.getLogger(f"weagent.sandbox.{name}")


def log_event(event_name: str, level: str = "info", **fields: Any) -> None:
    logger = configure_logging()
    safe_fields = {k: _json_safe(v) for k, v in fields.items()}
    suffix = ""
    if safe_fields:
        suffix = " " + json.dumps(safe_fields, ensure_ascii=False, separators=(",", ":"))
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn("%s%s", event_name, suffix)


def log_exception(event_name: str, **fields: Any) -> None:
    logger = configure_logging()
    safe_fields = {k: _json_safe(v) for k, v in fields.items()}
    suffix = ""
    if safe_fields:
        suffix = " " + json.dumps(safe_fields, ensure_ascii=False, separators=(",", ":"))
    logger.exception("%s%s", event_name, suffix)


def log_agent(agent_id: str, event: str, level: str = "info", **fields: Any) -> None:
    """Write an agent-scoped structured log and mirror a concise line to stdout."""
    _ensure_dirs()
    payload = {
        "ts": time.time(),
        "agent_id": agent_id,
        "event": event,
        **{k: _json_safe(v) for k, v in fields.items()},
    }
    path = os.path.join(AGENT_LOG_DIR, f"{agent_id or 'unknown'}.jsonl")
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    log_event(f"agent_{event}", level=level, agent_id=agent_id, **fields)
