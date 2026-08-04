"""
container.tools — Tool registry + built-in tools for orchestrator.

Tools are Python callables that agents can invoke.
The orchestrator intercepts tool calls and executes them.
"""

import base64
import csv
import json
import mimetypes
import os
import re
import shlex
import sqlite3
import struct
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from ..capabilities import (
    append_tool_call_record,
    now_iso,
    permissions_for_tool,
    resolve_bound_tool_capability,
    summarize_tool_input,
    summarize_tool_output,
)


# 无需能力绑定即可使用的工具（由运行时环境自动提供）
_ALWAYS_ALLOWED_TOOLS = {
    "rag_search": True,
    "call_service_api": True,
    "list_services": True,
}


class ToolRegistry:
    """Registry of tools available to agents."""

    TOOL_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')

    def __init__(self, workspace_root: str = "/workspace"):
        self._tools: dict[str, dict] = {}
        self.workspace_root = os.path.realpath(workspace_root)

    def register(self, name: str, fn: Callable, description: str = ""):
        if not self.TOOL_NAME_RE.match(name):
            raise ValueError(f"Invalid tool name: '{name}'. Must match {self.TOOL_NAME_RE.pattern}")
        self._tools[name] = {"fn": fn, "description": description or name}

    def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found")
        global WORKSPACE_ROOT
        previous_root = WORKSPACE_ROOT
        WORKSPACE_ROOT = self.workspace_root
        try:
            return tool["fn"](**kwargs)
        finally:
            WORKSPACE_ROOT = previous_root

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": i["description"]} for n, i in self._tools.items()]

    def call_from_agent(self, agent_id: str, tool_name: str, args: dict,
                        run_id: str = None, session_id: str = None) -> str:
        started_at = now_iso()
        tool_capability = resolve_bound_tool_capability(
            agent_id,
            tool_name,
            workspace_root=self.workspace_root,
        )
        permissions_used = permissions_for_tool(tool_name)

        def _record(status: str, result=None, error: str = None):
            if not tool_capability or not run_id:
                return
            append_tool_call_record(
                {
                    "session_id": session_id or "",
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "capability_id": tool_capability.get("capability_id"),
                    "capability_version_id": tool_capability.get("capability_version_id"),
                    "call_type": "tool",
                    "tool_name": tool_name,
                    "permissions_used": permissions_used,
                    "input_summary": summarize_tool_input(tool_name, args or {}),
                    "output_summary": summarize_tool_output(result) if error is None else {},
                    "status": status,
                    "error": error,
                    "started_at": started_at,
                    "completed_at": now_iso(),
                },
                workspace_root=self.workspace_root,
            )

        try:
            if tool_capability:
                status = tool_capability.get("status") or "implemented"
                if status not in {"implemented", "partial"}:
                    raise PermissionError(
                        f"Tool {tool_name} is not executable in current status: {status}"
                    )
                granted = set(tool_capability.get("granted_permissions") or [])
                missing = sorted(set(permissions_used) - granted)
                if missing:
                    raise PermissionError(
                        f"Missing granted permissions for {tool_name}: {', '.join(missing)}"
                    )
            elif not _ALWAYS_ALLOWED_TOOLS.get(tool_name) and _projection_exists(self.workspace_root):
                raise PermissionError(
                    f"Tool {tool_name} is not bound to agent {agent_id}"
                )
            execute_args = dict(args or {})
            if tool_capability and tool_capability.get("provider_config"):
                execute_args["_weagent_provider_config"] = tool_capability.get("provider_config")
            result = self.execute(tool_name, **execute_args)
            _record("completed", result=result)
            return json.dumps({"status": "ok", "result": result}, ensure_ascii=False)
        except Exception as e:
            _record("failed", error=str(e))
            return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ===== Built-in tool implementations =====

WORKSPACE_ROOT = os.path.realpath("/workspace")


def _projection_exists(workspace_root: str) -> bool:
    return os.path.exists(os.path.join(workspace_root, ".weagent", "capabilities", "index.json"))


def _resolve_workspace_path(path: str) -> str:
    full = os.path.join(WORKSPACE_ROOT, path.lstrip("/"))
    real = os.path.realpath(full)
    if real != WORKSPACE_ROOT and not real.startswith(WORKSPACE_ROOT + os.sep):
        raise ValueError("Access denied: path outside workspace")
    return real


def _relative_workspace_path(path: str) -> str:
    return os.path.relpath(path, WORKSPACE_ROOT).replace("\\", "/")


def _read_text_file(path: str, max_chars: int = 200_000) -> tuple[str, bool]:
    full = _resolve_workspace_path(path)
    if not os.path.exists(full):
        raise FileNotFoundError(f"File not found: {path}")
    with open(full, encoding="utf-8", errors="replace") as handle:
        content = handle.read(max_chars + 1)
    return content[:max_chars], len(content) > max_chars


def _skip_dir(name: str) -> bool:
    return name in {".git", ".weagent", "node_modules", ".npm-cache", ".pytest-tmp", "__pycache__"}


def _read_file(path: str) -> str:
    full = _resolve_workspace_path(path)
    if not os.path.exists(full):
        return f"File not found: {path}"
    with open(full, encoding="utf-8", errors="replace") as f:
        return f.read()


def _write_file(path: str, content: str) -> str:
    full = _resolve_workspace_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written: {path}"


def _run_command(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60, cwd="/workspace")
    out = result.stdout
    if result.stderr:
        out += f"\n[stderr]\n{result.stderr}"
    return out


def _report_progress(agent_id: str, progress: str, status: str) -> str:
    import json as _json
    data = _json.dumps({"agent_id": agent_id, "progress": progress, "status": status})
    os.makedirs("/workspace/.session", exist_ok=True)
    with open(f"/workspace/.session/progress_{agent_id}.json", "w") as f:
        f.write(data)
    return f"Progress: {progress} - {status}"


def _list_files(path: str = "") -> str:
    full = _resolve_workspace_path(path or "")
    if not os.path.exists(full):
        return f"Path not found: {path}"
    lines = []
    for root, dirs, files in os.walk(full):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        rel = os.path.relpath(root, WORKSPACE_ROOT)
        if rel == ".":
            rel = ""
        for f in files:
            lines.append(os.path.join(rel, f))
    return "\n".join(lines) if lines else "(empty)"


def _code_search(query: str, path: str = "", max_results: int = 50) -> dict:
    query = str(query or "")
    if not query:
        raise ValueError("query is required")
    max_results = max(1, min(int(max_results or 50), 200))
    start = _resolve_workspace_path(path or "")
    if not os.path.exists(start):
        raise FileNotFoundError(f"Path not found: {path}")
    matches = []
    for root, dirs, files in os.walk(start):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for filename in files:
            full = os.path.join(root, filename)
            try:
                with open(full, encoding="utf-8", errors="ignore") as handle:
                    for line_no, line in enumerate(handle, start=1):
                        if query in line:
                            matches.append({
                                "path": _relative_workspace_path(full),
                                "line": line_no,
                                "preview": line.rstrip("\n")[:300],
                            })
                            if len(matches) >= max_results:
                                return {"query": query, "matches": matches, "truncated": True}
            except OSError:
                continue
    return {"query": query, "matches": matches, "truncated": False}


def _code_review_scan(path: str) -> dict:
    content, _truncated = _read_text_file(path, max_chars=200_000)
    findings = []
    rules = [
        ("todo", re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE), "TODO/FIXME marker"),
        (
            "secret_like",
            re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]", re.IGNORECASE),
            "Secret-like assignment",
        ),
        (
            "dangerous_api",
            re.compile(r"\b(eval|exec|subprocess\.|os\.system|shell=True)\b"),
            "Dangerous API usage",
        ),
    ]
    for line_no, line in enumerate(content.splitlines(), start=1):
        for rule, pattern, message in rules:
            if pattern.search(line):
                findings.append({
                    "rule": rule,
                    "line": line_no,
                    "message": message,
                    "preview": line.strip()[:220],
                })
    return {"path": path, "findings": findings}


def _document_text_extract(path: str, max_chars: int = 20_000) -> dict:
    allowed = {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".vue", ".yaml", ".yml"}
    ext = os.path.splitext(path)[1].lower()
    if ext not in allowed:
        raise ValueError(f"Unsupported text document extension: {ext or '(none)'}")
    text, truncated = _read_text_file(path, max_chars=max(100, min(int(max_chars or 20_000), 200_000)))
    return {"path": path, "text": text, "truncated": truncated}


def _csv_profile(path: str, sample_rows: int = 5) -> dict:
    full = _resolve_workspace_path(path)
    with open(full, newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        row_count = 0
        empty_counts = {column: 0 for column in columns}
        samples = []
        for row in reader:
            row_count += 1
            if len(samples) < sample_rows:
                samples.append(row)
            for column in columns:
                if row.get(column) in {"", None}:
                    empty_counts[column] += 1
    return {
        "path": path,
        "columns": columns,
        "row_count": row_count,
        "empty_counts": empty_counts,
        "sample_rows": samples,
    }


def _json_query(path: str, query: str = "") -> dict:
    full = _resolve_workspace_path(path)
    with open(full, encoding="utf-8") as handle:
        data = json.load(handle)
    current = data
    if query:
        for part in str(query).split("."):
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
            else:
                raise ValueError(f"Cannot descend into {part}")
    return {"path": path, "query": query, "result": current}


def _sqlite_query_readonly(path: str, query: str, max_rows: int = 50) -> dict:
    sql = str(query or "").strip()
    if not re.match(r"^(select|pragma\s+table_info)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT and PRAGMA table_info queries are allowed")
    if ";" in sql.rstrip(";"):
        raise ValueError("Only one SQL statement is allowed")
    full = _resolve_workspace_path(path)
    conn = sqlite3.connect(f"file:{full}?mode=ro", uri=True)
    try:
        cursor = conn.execute(sql)
        columns = [item[0] for item in cursor.description or []]
        rows = cursor.fetchmany(max(1, min(int(max_rows or 50), 200)))
    finally:
        conn.close()
    return {"path": path, "columns": columns, "rows": rows, "row_count": len(rows)}


def _image_info(path: str) -> dict:
    full = _resolve_workspace_path(path)
    size = os.path.getsize(full)
    with open(full, "rb") as handle:
        header = handle.read(32)
    mime_type, _encoding = mimetypes.guess_type(full)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", header[16:24])
        image_format = "PNG"
    elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        width, height = struct.unpack("<HH", header[6:10])
        image_format = "GIF"
    elif header.startswith(b"\xff\xd8"):
        image_format, width, height = "JPEG", None, None
    else:
        raise ValueError("Unsupported image format")
    return {
        "path": path,
        "format": image_format,
        "mime_type": mime_type or "application/octet-stream",
        "size": size,
        "width": width,
        "height": height,
    }


def _run_command_safe(command: str, timeout: int = 30) -> dict:
    command = str(command or "").strip()
    if not command:
        raise ValueError("command is required")
    if re.search(r"[;&|`$<>]", command):
        raise ValueError("Shell operators are not allowed")
    parts = shlex.split(command)
    if not parts:
        raise ValueError("command is required")
    allowed = {"echo", "pwd", "ls", "dir", "python"}
    if parts[0] not in allowed:
        raise ValueError(f"Command not allowed: {parts[0]}")
    if parts[0] == "echo":
        return {"exit_code": 0, "stdout": " ".join(parts[1:]) + "\n", "stderr": ""}
    if parts[0] == "pwd":
        return {"exit_code": 0, "stdout": WORKSPACE_ROOT + "\n", "stderr": ""}
    if parts[0] in {"ls", "dir"}:
        target = _resolve_workspace_path(parts[1] if len(parts) > 1 else "")
        return {
            "exit_code": 0,
            "stdout": "\n".join(sorted(os.listdir(target)))[:20_000],
            "stderr": "",
        }
    if parts[0] == "python" and parts[1:] not in (["--version"], ["-V"]):
        raise ValueError("Only python --version is allowed")
    result = subprocess.run(
        parts,
        cwd=WORKSPACE_ROOT,
        shell=False,
        capture_output=True,
        text=True,
        timeout=max(1, min(int(timeout or 30), 60)),
    )
    return {
        "exit_code": result.returncode,
        "stdout": (result.stdout or "")[:20_000],
        "stderr": (result.stderr or "")[:20_000],
    }


def _git_command(args: list[str]) -> dict:
    result = subprocess.run(
        ["git", *args],
        cwd=WORKSPACE_ROOT,
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "exit_code": result.returncode,
        "stdout": (result.stdout or "")[:20_000],
        "stderr": (result.stderr or "")[:20_000],
    }


def _git_status(path: str = "") -> dict:
    return _git_command(["status", "--short", "--", path] if path else ["status", "--short"])


def _git_diff(path: str = "") -> dict:
    return _git_command(["diff", "--", path] if path else ["diff"])


def _git_log(limit: int = 5) -> dict:
    safe_limit = max(1, min(int(limit or 5), 20))
    return _git_command(["log", f"--max-count={safe_limit}", "--oneline"])


def _http_fetch(url: str, max_bytes: int = 40_000) -> dict:
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    limit = max(100, min(int(max_bytes or 40_000), 200_000))
    request = urllib.request.Request(url, headers={"User-Agent": "WeAgent-Tool/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read(limit + 1)
            status_code = getattr(response, "status", 200)
            content_type = response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read(limit + 1)
        status_code = exc.code
        content_type = exc.headers.get("content-type", "")
    text = body[:limit].decode("utf-8", errors="replace")
    return {
        "url": urllib.parse.urlunparse(parsed._replace(query="", fragment="")),
        "status_code": status_code,
        "content_type": content_type,
        "body_preview": text,
        "truncated": len(body) > limit,
    }


def _api_request(url: str, method: str = "GET", headers: dict = None,
                 body: str = "", max_bytes: int = 40_000) -> dict:
    method = str(method or "GET").upper()
    if method not in {"GET", "POST"}:
        raise ValueError("Only GET and POST are allowed")
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    safe_headers = {}
    for key, value in (headers or {}).items():
        if key.lower() in {"authorization", "cookie"}:
            continue
        safe_headers[key] = value
    data = body.encode("utf-8") if method == "POST" and body else None
    request = urllib.request.Request(url, data=data, headers=safe_headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read(max(100, min(int(max_bytes or 40_000), 200_000)))
        return {
            "url": urllib.parse.urlunparse(parsed._replace(query="", fragment="")),
            "method": method,
            "status_code": getattr(response, "status", 200),
            "content_type": response.headers.get("content-type", ""),
            "body_preview": raw.decode("utf-8", errors="replace"),
        }


def _require_provider_config(provider_config: dict | None) -> dict:
    provider_config = provider_config or {}
    if provider_config.get("status") != "valid":
        raise ValueError("Valid provider_config is required")
    return provider_config


def _configured_web_search(query: str, max_results: int = 5,
                           _weagent_provider_config: dict = None) -> dict:
    provider = _require_provider_config(_weagent_provider_config)
    config = provider.get("config") or {}
    if provider.get("provider_type") != "http":
        raise ValueError("Only http provider is supported by the sandbox web_search adapter")
    endpoint = str(config.get("endpoint") or "").strip()
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("Configured search endpoint must be http/https")
    parsed = urllib.parse.urlparse(endpoint)
    params = urllib.parse.parse_qs(parsed.query)
    params["q"] = [str(query or "")]
    params["limit"] = [str(max(1, min(int(max_results or 5), 20)))]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(params, doseq=True)))
    request = urllib.request.Request(url, headers={"User-Agent": "WeAgent-Search/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read(80_000)
        content_type = response.headers.get("content-type", "")
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {"body_preview": text[:10_000]}
    results = payload.get("results") if isinstance(payload, dict) else None
    return {
        "query": query,
        "provider_profile": provider.get("profile_name"),
        "provider_type": provider.get("provider_type"),
        "status_code": getattr(response, "status", 200),
        "content_type": content_type,
        "results": results or [],
        "raw": payload if not results else {},
    }


def _configured_image_analysis(path: str, prompt: str = "",
                               _weagent_provider_config: dict = None) -> dict:
    provider = _require_provider_config(_weagent_provider_config)
    image = _image_info(path)
    return {
        "provider_profile": provider.get("profile_name"),
        "provider_type": provider.get("provider_type"),
        "model": (provider.get("config") or {}).get("model", ""),
        "prompt": prompt,
        "image": image,
        "analysis": (
            f"{image['format']} image, {image.get('width')}x{image.get('height')}, "
            f"{image.get('size')} bytes"
        ),
    }


def _configured_image_generate(prompt: str, output_path: str = "generated/image.png",
                               _weagent_provider_config: dict = None) -> dict:
    provider = _require_provider_config(_weagent_provider_config)
    config = provider.get("config") or {}
    output_path = str(output_path or "generated/image.png")
    if not output_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise ValueError("output_path must end with png, jpg, jpeg, or webp")
    if not output_path.lower().endswith(".png"):
        raise ValueError("sandbox fixture image generator currently writes png output")
    full = _resolve_workspace_path(output_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
        "WjR9awAAAABJRU5ErkJggg=="
    )
    with open(full, "wb") as handle:
        handle.write(png)
    return {
        "provider_profile": provider.get("profile_name"),
        "provider_type": provider.get("provider_type"),
        "model": config.get("model", ""),
        "prompt": prompt,
        "path": _relative_workspace_path(full),
        "format": "PNG",
        "width": 1,
        "height": 1,
    }


def _configured_database_query(query: str, max_rows: int = 50,
                               _weagent_provider_config: dict = None) -> dict:
    provider = _require_provider_config(_weagent_provider_config)
    config = provider.get("config") or {}
    if provider.get("provider_type") != "database":
        raise ValueError("database_query requires a database provider")
    if config.get("readonly") is not True:
        raise ValueError("database_query requires readonly provider config")
    driver = config.get("driver") or "sqlite"
    if driver != "sqlite":
        raise ValueError("sandbox database_query adapter currently supports sqlite fixtures")
    path = config.get("path") or config.get("database_path")
    if not path:
        raise ValueError("sqlite database provider config requires path")
    result = _sqlite_query_readonly(path=path, query=query, max_rows=max_rows)
    result["provider_profile"] = provider.get("profile_name")
    result["provider_type"] = provider.get("provider_type")
    return result


def _list_services() -> dict:
    """List all available microservices from the service registry.

    Returns a dict with a 'services' key mapping service_name -> base_url.
    """
    registry_raw = os.environ.get("SERVICE_REGISTRY", "{}")
    try:
        services = json.loads(registry_raw) if registry_raw else {}
    except json.JSONDecodeError:
        services = {}
    return {"services": services}


def _call_service_api(service_name: str, method: str = "GET",
                      path: str = "/", body: dict = None,
                      query_params: dict = None) -> dict:
    """Call a microservice API endpoint generically.

    Args:
        service_name: Name of the service (e.g. 'rag', 'rd', 'edu', 'office')
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: API path (e.g. '/api/rag/search', '/api/rd/spec')
        body: JSON-serializable dict for the request body (for POST/PUT)
        query_params: Optional dict of query string parameters

    Returns:
        The parsed JSON response from the service.
    """
    registry_raw = os.environ.get("SERVICE_REGISTRY", "{}")
    try:
        services = json.loads(registry_raw) if registry_raw else {}
    except json.JSONDecodeError:
        return {"status": "error", "error": "SERVICE_REGISTRY is not valid JSON"}

    base_url = services.get(service_name)
    if not base_url:
        return {
            "status": "error",
            "error": f"Unknown service '{service_name}'. Available: {list(services.keys())}",
        }

    url = f"{base_url.rstrip('/')}{path}"
    if query_params:
        url += "?" + urllib.parse.urlencode(query_params)

    data = json.dumps(body).encode("utf-8") if body else None

    user_auth = os.environ.get("USER_AUTH_TOKEN", "")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "WeAgent-ServiceCall/1.0",
    }
    if user_auth:
        # Primary auth: user's JWT token (all services share the same JWT secret)
        headers["Authorization"] = user_auth
    else:
        # Fallback: internal API key for background tasks without user context
        api_key = os.environ.get("RAG_INTERNAL_API_KEY", "")
        if api_key:
            headers["X-Internal-API-Key"] = api_key

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            return json.loads(resp_body)
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "status": "error",
            "http_code": exc.code,
            "error": f"Service {service_name} returned HTTP {exc.code}",
            "detail": err_body[:1000],
        }
    except urllib.error.URLError as exc:
        return {
            "status": "error",
            "error": f"Cannot connect to service '{service_name}' at {base_url}: {exc.reason}",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---- Backward-compatible rag_search (delegates to call_service_api) ----
def _rag_search(query: str, top_k: int = 5, domain: str = "",
                workspace_id: str = "", score_threshold: float = 0.0,
                document_ids: list = None) -> dict:
    """Search the RAG knowledge base (delegates to call_service_api for rag service).

    Kept for backward compatibility — agents can also use call_service_api directly.
    """
    if not query or not str(query).strip():
        return {"query": query, "results": [], "total": 0}

    # Normalize document_ids — try param first, then config file, then env var
    doc_ids = None
    if document_ids:
        doc_ids = [str(d) for d in document_ids if d]
    if not doc_ids:
        _config_path = os.path.join(os.path.dirname(__file__), "kb_config.json")
        try:
            if os.path.exists(_config_path):
                with open(_config_path, "r", encoding="utf-8") as _f:
                    _config = json.loads(_f.read())
                    _ids = _config.get("kb_document_ids")
                    if _ids:
                        doc_ids = [str(d) for d in _ids if d]
        except Exception:
            pass
    if not doc_ids:
        _env_ids = os.environ.get("KB_DOCUMENT_IDS", "")
        if _env_ids:
            try:
                _parsed = json.loads(_env_ids)
                if isinstance(_parsed, list):
                    doc_ids = [str(d) for d in _parsed if d]
            except Exception:
                pass

    result = _call_service_api("rag", "POST", "/api/rag/search", body={
        "query": str(query or ""),
        "top_k": max(1, min(int(top_k or 5), 20)),
        "domain": str(domain or "").strip() or None,
        "workspace_id": str(workspace_id or "").strip() or None,
        "score_threshold": max(0.0, min(float(score_threshold or 0.0), 1.0)),
        "document_ids": doc_ids,
    })

    if result.get("status") == "error":
        raise RuntimeError(f"知识库检索失败: {result.get('error', 'unknown')}")

    data = result.get("data", {})
    return {
        "query": data.get("query", query),
        "results": data.get("results", []),
        "total": data.get("total", 0),
    }


def register_builtin_tools(registry: ToolRegistry):
    """Register all built-in tools."""
    registry.register("read_file", _read_file, "Read a file from workspace")
    registry.register("write_file", _write_file, "Write content to a file")
    registry.register("run_command", _run_command, "Run a shell command")
    registry.register("report_progress", _report_progress, "Report execution progress")
    registry.register("list_files", _list_files, "List files in workspace")
    registry.register("code_search", _code_search, "Search text in workspace")
    registry.register("code_review_scan", _code_review_scan, "Run deterministic code risk scan")
    registry.register("document_text_extract", _document_text_extract, "Extract text from supported documents")
    registry.register("http_fetch", _http_fetch, "Fetch text from a known URL")
    registry.register("web_search", _configured_web_search, "Search through a configured provider")
    registry.register("api_request", _api_request, "Call an HTTP API")
    registry.register("csv_profile", _csv_profile, "Profile a CSV file")
    registry.register("json_query", _json_query, "Read a JSON file or key path")
    registry.register("sqlite_query_readonly", _sqlite_query_readonly, "Run read-only SQLite query")
    registry.register("database_query", _configured_database_query, "Run a configured read-only database query")
    registry.register("image_info", _image_info, "Inspect local image metadata")
    registry.register("image_analysis", _configured_image_analysis, "Analyze an image through a configured provider")
    registry.register("image_generate", _configured_image_generate, "Generate an image through a configured provider")
    registry.register("run_command_safe", _run_command_safe, "Run an allowlisted command")
    registry.register("git_status", _git_status, "Read git status")
    registry.register("git_diff", _git_diff, "Read git diff")
    registry.register("git_log", _git_log, "Read git log")
    registry.register("rag_search", _rag_search, "Search the RAG knowledge base for relevant document chunks")
    registry.register("list_services", _list_services, "List all available microservices and their base URLs")
    registry.register("call_service_api", _call_service_api, "Call a microservice API endpoint generically (discover via /api/spec)")
