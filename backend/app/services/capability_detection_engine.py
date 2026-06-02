import ast
import re
from pathlib import PurePosixPath


_SCRIPT_SUFFIXES = {".js", ".mjs", ".ts", ".py", ".sh", ".ps1"}
_NETWORK_PATTERNS = [
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\brequests\."),
    re.compile(r"\burllib\b"),
    re.compile(r"\bsocket\b"),
    re.compile(r"\bcurl\b"),
    re.compile(r"\bwget\b"),
]
_SHELL_CONTROL_PATTERN = re.compile(r"(\|\||&&|[;|<>]|\$\(|`)")
_SECRET_PATTERN = re.compile(r"(\.env|\.ssh|id_rsa|API_KEY|TOKEN|SECRET|PRIVATE_KEY)", re.I)
_ABS_PATH_PATTERN = re.compile(r"(^|[\s'\"=])(/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")

_JS_DANGEROUS = {
    "child_process": "run_command",
    "fs.rm": "write_workspace",
    "fs.unlink": "write_workspace",
    "eval": "run_command",
    "Function": "run_command",
}
_PY_DANGEROUS = {
    "subprocess": "run_command",
    "os.system": "run_command",
    "eval": "run_command",
    "exec": "run_command",
    "socket": "network",
    "requests": "network",
    "urllib": "network",
    "shutil.rmtree": "write_workspace",
}
_SHELL_DANGEROUS = {
    "rm -rf": "write_workspace",
    "curl": "network",
    "wget": "network",
    "chmod +x": "run_command",
}


def audit_files(files: list[dict]) -> dict:
    """Best-effort static detector for imported Skill bundle files."""
    risk_items = []
    inferred_permissions = set()
    scanned_files = []

    for file_record in files or []:
        path = str(file_record.get("path") or "")
        content = str(file_record.get("content") or "")
        scanned_files.append(path)
        suffix = PurePosixPath(path.replace("\\", "/")).suffix.lower()
        if suffix in _SCRIPT_SUFFIXES:
            risk_items.extend(_syntax_items(path, suffix, content))
        risk_items.extend(_lexical_items(path, content))
        risk_items.extend(_illegal_library_items(path, suffix, content))
        risk_items.extend(_illegal_operation_items(path, content))

    for item in risk_items:
        permission = item.get("suggested_permission")
        if permission:
            inferred_permissions.add(permission)

    return {
        "risk_level": _risk_level(risk_items),
        "risk_items": risk_items,
        "blocking_items": [
            item for item in risk_items
            if item.get("severity") == "high" and item.get("category") in {
                "secret_access",
                "illegal_operation",
                "path_escape",
            }
        ],
        "inferred_permissions": sorted(inferred_permissions),
        "scanned_files": scanned_files,
    }


def _syntax_items(path: str, suffix: str, content: str) -> list[dict]:
    if suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as exc:
            return [
                _item(
                    "syntax",
                    "medium",
                    path,
                    exc.lineno,
                    "Python syntax error",
                    exc.text or content.splitlines()[0] if content else "",
                )
            ]
    if suffix in {".js", ".mjs", ".ts"}:
        if _has_unbalanced_delimiters(content):
            return [_item("syntax", "medium", path, None, "JavaScript syntax appears unbalanced", "delimiter")]
    if suffix in {".sh", ".ps1"}:
        if _has_unbalanced_quotes(content):
            return [_item("syntax", "medium", path, None, "Shell syntax appears to contain unbalanced quotes", "quote")]
    return []


def _lexical_items(path: str, content: str) -> list[dict]:
    items = []
    if _SHELL_CONTROL_PATTERN.search(content):
        items.append(_item("lexical", "medium", path, None, "Shell control operator detected", _SHELL_CONTROL_PATTERN.search(content).group(0), "run_command"))
    if _SECRET_PATTERN.search(content):
        evidence = _SECRET_PATTERN.search(content).group(0)
        items.append(_item("secret_access", "high", path, None, "Secret or private-key access pattern detected", evidence, "use_secret"))
    if ".." in content or _ABS_PATH_PATTERN.search(content):
        evidence = ".." if ".." in content else _ABS_PATH_PATTERN.search(content).group(0)
        items.append(_item("path_escape", "high", path, None, "Path may escape workspace scope", evidence, "write_workspace"))
    for pattern in _NETWORK_PATTERNS:
        match = pattern.search(content)
        if match:
            items.append(_item("network_access", "medium", path, None, "Network access pattern detected", match.group(0), "network"))
            break
    return items


def _illegal_library_items(path: str, suffix: str, content: str) -> list[dict]:
    items = []
    patterns = {}
    if suffix in {".js", ".mjs", ".ts"}:
        patterns = _JS_DANGEROUS
    elif suffix == ".py":
        patterns = _PY_DANGEROUS
    elif suffix in {".sh", ".ps1"}:
        patterns = _SHELL_DANGEROUS
    else:
        patterns = {**_JS_DANGEROUS, **_PY_DANGEROUS, **_SHELL_DANGEROUS}

    for token, permission in patterns.items():
        if token in content:
            items.append(
                _item(
                    "illegal_library",
                    "medium" if permission != "use_secret" else "high",
                    path,
                    _line_number(content, token),
                    f"Dangerous library or API detected: {token}",
                    token,
                    permission,
                )
            )
    return items


def _illegal_operation_items(path: str, content: str) -> list[dict]:
    checks = [
        (r"rm\s+-rf\b", "Destructive delete operation detected", "write_workspace"),
        (r"curl\b.+\|\s*(sh|bash)", "Remote download piped to shell detected", "run_command"),
        (r"wget\b.+\|\s*(sh|bash)", "Remote download piped to shell detected", "run_command"),
        (r"chmod\s+\+x\b.+\n.*\./", "Download-and-execute style operation detected", "run_command"),
    ]
    items = []
    for pattern, message, permission in checks:
        match = re.search(pattern, content, re.S)
        if match:
            items.append(
                _item(
                    "illegal_operation",
                    "high",
                    path,
                    _line_number(content, match.group(0).splitlines()[0]),
                    message,
                    match.group(0).splitlines()[0],
                    permission,
                )
            )
    return items


def _item(category: str, severity: str, path: str, line, message: str,
          evidence: str, permission: str | None = None) -> dict:
    return {
        "category": category,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "evidence": evidence,
        "suggested_permission": permission,
    }


def _risk_level(items: list[dict]) -> str:
    severities = {item.get("severity") for item in items}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _line_number(content: str, needle: str):
    if not needle:
        return None
    for index, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            return index
    return None


def _has_unbalanced_quotes(content: str) -> bool:
    return content.count("'") % 2 == 1 or content.count('"') % 2 == 1


def _has_unbalanced_delimiters(content: str) -> bool:
    pairs = [("(", ")"), ("{", "}"), ("[", "]")]
    return any(content.count(opening) != content.count(closing) for opening, closing in pairs)
