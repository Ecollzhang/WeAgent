import re
import shlex
from pathlib import PurePosixPath


class ImportSecurityError(ValueError):
    """Raised when an external import source violates allowlist rules."""


_SHELL_META_PATTERN = re.compile(r"(\|\||&&|[;|<>`])")
_WRAPPER_COMMANDS = {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe"}
_BINARY_SUFFIXES = {".exe", ".dll", ".so", ".dylib", ".bat", ".cmd"}
_SENSITIVE_NAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
_SENSITIVE_SUFFIXES = {".pem", ".key"}
_CACHE_DIRS = {"node_modules", ".git", ".npm", ".npm-cache", ".pnpm-store", "_cacache"}


def parse_npx_import_source(source: str) -> dict:
    """Parse an allowed npx import source without invoking a shell."""
    text = (source or "").strip()
    if not text:
        raise ImportSecurityError("npx source is required")
    if _SHELL_META_PATTERN.search(text):
        raise ImportSecurityError("Shell control operators are not allowed")

    try:
        tokens = shlex.split(text, posix=True)
    except ValueError as exc:
        raise ImportSecurityError("Invalid command quoting") from exc

    if not tokens or tokens[0].lower() in _WRAPPER_COMMANDS:
        raise ImportSecurityError("Shell wrappers are not allowed")
    if tokens[0].lower() != "npx":
        raise ImportSecurityError("Only npx import sources are supported")
    if any(token.lower() in _WRAPPER_COMMANDS for token in tokens[1:]):
        raise ImportSecurityError("Shell wrappers are not allowed")
    if any(token.startswith("-") for token in tokens[1:]):
        raise ImportSecurityError("npx flags are not allowed in v1 import sources")

    if len(tokens) == 4 and tokens[1:3] == ["skills", "add"]:
        source_ref = tokens[3]
        _validate_package_or_repo_ref(source_ref)
        return {
            "kind": "npx_skills_add",
            "command": "npx",
            "args": ["skills", "add", "--yes", "--global", source_ref],
            "package": "skills",
            "source": source_ref,
        }

    if len(tokens) == 2:
        package = tokens[1]
        _validate_package_or_repo_ref(package)
        return {
            "kind": "npx_package",
            "command": "npx",
            "args": [package],
            "package": package,
            "source": "",
        }

    raise ImportSecurityError("Unsupported npx import form")


def validate_bundle_files(files: list[dict]) -> dict:
    """Validate uploaded or discovered bundle file metadata."""
    risk_items = []
    blocking_items = []
    scanned = []
    for item in files or []:
        path = str(item.get("path") or "")
        scanned.append(path)
        normalized = _normalize_bundle_path(path)
        path_items = _validate_path(path, normalized)
        for risk in path_items:
            risk_items.append(risk)
            if risk["severity"] == "high":
                blocking_items.append(risk)

    risk_level = _risk_level(risk_items)
    return {
        "risk_level": risk_level,
        "risk_items": risk_items,
        "blocking_items": blocking_items,
        "inferred_permissions": [],
        "scanned_files": scanned,
    }


def _validate_package_or_repo_ref(value: str):
    if not value or value.startswith("."):
        raise ImportSecurityError("Invalid package or repo reference")
    if _SHELL_META_PATTERN.search(value) or "\\" in value:
        raise ImportSecurityError("Invalid package or repo reference")
    if value.startswith(("http://", "https://")) and "github.com/" not in value:
        raise ImportSecurityError("Only GitHub URLs are supported")


def _normalize_bundle_path(path: str) -> PurePosixPath:
    return PurePosixPath(path.replace("\\", "/"))


def _validate_path(path: str, normalized: PurePosixPath) -> list[dict]:
    items = []
    parts = [part for part in normalized.parts if part not in {"", "."}]
    lower_parts = [part.lower() for part in parts]
    name = lower_parts[-1] if lower_parts else ""
    suffix = normalized.suffix.lower()

    if (
        not path
        or normalized.is_absolute()
        or ".." in parts
        or re.match(r"^[a-zA-Z]:", path)
    ):
        items.append(_item("path_traversal", "high", path, "Path escapes the bundle root"))

    if any(part in _CACHE_DIRS for part in lower_parts):
        items.append(_item("package_cache", "high", path, "Package cache directories are not allowed"))

    if any(part == ".ssh" for part in lower_parts) or name in _SENSITIVE_NAMES or suffix in _SENSITIVE_SUFFIXES:
        items.append(_item("sensitive_file", "high", path, "Sensitive files cannot be imported"))

    if suffix in _BINARY_SUFFIXES:
        items.append(_item("binary_executable", "high", path, "Binary or executable files cannot be imported"))

    return items


def _item(category: str, severity: str, path: str, message: str, permission: str | None = None) -> dict:
    return {
        "category": category,
        "severity": severity,
        "path": path,
        "line": None,
        "message": message,
        "evidence": path,
        "suggested_permission": permission,
    }


def _risk_level(items: list[dict]) -> str:
    severities = {item.get("severity") for item in items}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"
