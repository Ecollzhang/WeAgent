"""
Provider CLI health checks for the sandbox container.

Phase 1 only verifies the CLIs are present and reports their versions. It does
not select providers for agents or change the existing Claude execution path.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


DEFAULT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    command: str
    version_args: tuple[str, ...] = ("--version",)


PROVIDER_SPECS: dict[str, ProviderSpec] = {
    "claude": ProviderSpec(name="claude", command="claude"),
    "codex": ProviderSpec(name="codex", command="codex"),
    "opencode": ProviderSpec(name="opencode", command="opencode"),
}


def check_provider(
    name: str,
    spec: Optional[ProviderSpec] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Return CLI availability and version details for a provider."""
    spec = spec or PROVIDER_SPECS.get(name)
    if spec is None:
        return {
            "name": name,
            "available": False,
            "command": name,
            "path": None,
            "version": "",
            "error": f"Unsupported provider: {name}",
        }

    path = shutil.which(spec.command)
    if not path:
        return {
            "name": spec.name,
            "available": False,
            "command": spec.command,
            "path": None,
            "version": "",
            "error": f"{spec.command} CLI not found",
        }

    command = [spec.command, *spec.version_args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "name": spec.name,
            "available": False,
            "command": spec.command,
            "path": path,
            "version": "",
            "error": f"{spec.command} version check timed out after {timeout_seconds}s",
        }
    except Exception as exc:
        return {
            "name": spec.name,
            "available": False,
            "command": spec.command,
            "path": path,
            "version": "",
            "error": str(exc),
        }

    output = (result.stdout or result.stderr or "").strip()
    version = output.splitlines()[0].strip() if output else ""
    if result.returncode != 0:
        return {
            "name": spec.name,
            "available": False,
            "command": spec.command,
            "path": path,
            "version": version,
            "returncode": result.returncode,
            "error": output or f"{spec.command} version check failed",
        }

    return {
        "name": spec.name,
        "available": True,
        "command": spec.command,
        "path": path,
        "version": version,
        "returncode": result.returncode,
        "error": "",
    }


def get_provider_health(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, dict]:
    """Return health information for all supported sandbox providers."""
    return {
        name: check_provider(name, spec, timeout_seconds=timeout_seconds)
        for name, spec in PROVIDER_SPECS.items()
    }


def supported_providers() -> list[str]:
    return sorted(PROVIDER_SPECS)
