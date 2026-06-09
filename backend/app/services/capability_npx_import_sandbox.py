import subprocess
import tempfile
import shutil
from pathlib import Path

from app.services.capability_import_preview_service import (
    capability_import_preview_service,
)
from app.services.capability_import_security import (
    ImportSecurityError,
    parse_npx_import_source,
)

NPX_IMPORT_IMAGE = "node:22"


class CapabilityNpxImportSandbox:
    """Run allowlisted npx installers in a one-shot Docker import sandbox."""

    def preview_npx(self, user_id, source_ref, runner=None, timeout=180):
        try:
            parsed = parse_npx_import_source(source_ref)
        except ImportSecurityError as exc:
            return None, str(exc)

        runner = runner or self._default_runner
        temp_dir = tempfile.mkdtemp(prefix="weagent-npx-import-")
        try:
            import_root = Path(temp_dir)
            command = self._docker_command(parsed, import_root)
            try:
                result = runner(command, import_root, timeout)
            except subprocess.TimeoutExpired:
                return None, f"npx import sandbox timed out after {timeout} seconds"
            except FileNotFoundError:
                return None, "Docker import sandbox unavailable"
            except OSError as exc:
                return None, f"Docker import sandbox failed: {exc}"

            returncode = _returncode(result)
            if returncode != 0:
                return None, _error_message(result)

            preview, error = capability_import_preview_service.preview_directory(
                user_id=user_id,
                directory_path=import_root,
                source_ref=source_ref,
                source_type="npx",
            )
            if error:
                return None, error
            preview["import_logs"] = {
                "stdout": _stream(result, "stdout"),
                "stderr": _stream(result, "stderr"),
                "returncode": returncode,
            }
            return preview, None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _docker_command(self, parsed, import_root):
        container_home = "/import-home"
        return [
            "docker",
            "run",
            "--rm",
            "-e",
            f"HOME={container_home}",
            "-e",
            f"CODEX_HOME={container_home}/.codex",
            "-e",
            f"CLAUDE_HOME={container_home}/.claude",
            "-e",
            f"AGENTS_HOME={container_home}/.agents",
            "-e",
            "NPM_CONFIG_YES=true",
            "-e",
            "NPM_CONFIG_UPDATE_NOTIFIER=false",
            "-e",
            "NPM_CONFIG_FUND=false",
            "-e",
            "NPM_CONFIG_AUDIT=false",
            "-e",
            "NPM_CONFIG_LOGLEVEL=error",
            "-e",
            "NPM_CONFIG_PROGRESS=false",
            "-e",
            f"NPM_CONFIG_CACHE={container_home}/.npm-cache",
            "-v",
            f"{import_root}:{container_home}",
            "-w",
            container_home,
            NPX_IMPORT_IMAGE,
            "npx",
            "--yes",
            *parsed["args"],
        ]

    def _default_runner(self, command, _import_root, timeout):
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )


def _returncode(result):
    if isinstance(result, dict):
        return int(result.get("returncode", 0))
    return int(getattr(result, "returncode", 0))


def _stream(result, name):
    if isinstance(result, dict):
        return result.get(name, "")
    return getattr(result, name, "")


def _error_message(result):
    stderr = _stream(result, "stderr")
    stdout = _stream(result, "stdout")
    return stderr or stdout or "npx import sandbox failed"


capability_npx_import_sandbox = CapabilityNpxImportSandbox()
