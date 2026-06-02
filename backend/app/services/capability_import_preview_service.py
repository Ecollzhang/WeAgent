import json
import os
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from app import db
from app.models.capability import CapabilityImportJob
from app.services.capability_detection_engine import audit_files
from app.services.capability_import_security import validate_bundle_files


SUPPORTED_SKILL_LAYOUTS = (
    "SKILL.md",
    "*/SKILL.md",
    ".codex/skills/*/SKILL.md",
    ".claude/skills/*/SKILL.md",
    ".agents/skills/*/SKILL.md",
    "skills/*/SKILL.md",
)
IGNORED_IMPORT_DIRS = {
    ".git",
    ".npm",
    ".npm-cache",
    ".pnpm-store",
    "_cacache",
    "node_modules",
}


class CapabilityImportPreviewService:
    """Create static import previews without executing external code."""

    def preview_markdown(self, user_id, markdown, source_ref="markdown"):
        if markdown is None or not str(markdown).strip():
            return None, "Markdown is required"
        files = [{
            "path": "SKILL.md",
            "kind": "skill_md",
            "content": str(markdown),
            "size": len(str(markdown).encode("utf-8")),
        }]
        return self._create_preview(
            user_id=user_id,
            source_type="markdown",
            source_ref=source_ref or "markdown",
            files=files,
            skill_paths=["SKILL.md"],
        )

    def preview_zip_bundle(self, user_id, zip_bytes, source_ref="bundle.zip"):
        if not zip_bytes:
            return None, "Zip bundle is required"
        try:
            files = self._files_from_zip(zip_bytes)
        except (zipfile.BadZipFile, ValueError) as exc:
            return None, str(exc)
        skill_paths = self._find_skill_paths([item["path"] for item in files])
        manifest_candidates = self._manifest_capability_previews(files)
        if not skill_paths and not manifest_candidates:
            return None, "No SKILL.md or capability manifest files found in bundle"
        return self._create_preview(
            user_id=user_id,
            source_type="upload",
            source_ref=source_ref or "bundle.zip",
            files=files,
            skill_paths=skill_paths,
            manifest_candidates=manifest_candidates,
        )

    def preview_repo_static(self, user_id, repo_path, source_ref="repo"):
        return None, "Repo import is not exposed in v1. Use zip bundle upload instead."

    def preview_directory(self, user_id, directory_path, source_ref, source_type):
        root = Path(directory_path or "")
        if not root.exists() or not root.is_dir():
            return None, "Preview directory not found"
        files = self._files_from_directory(root)
        skill_paths = self._find_skill_paths([item["path"] for item in files])
        manifest_candidates = self._manifest_capability_previews(files)
        if not skill_paths and not manifest_candidates:
            return None, f"No SKILL.md or capability manifest files found in {source_type} output"
        return self._create_preview(
            user_id=user_id,
            source_type=source_type,
            source_ref=source_ref,
            files=files,
            skill_paths=skill_paths,
            manifest_candidates=manifest_candidates,
        )

    def confirm_import_job(self, import_job_id):
        job = CapabilityImportJob.query.get(import_job_id)
        if not job:
            return None, "Import job not found"
        return job.preview_payload or {}, None

    def _create_preview(self, user_id, source_type, source_ref, files, skill_paths,
                        manifest_candidates=None):
        manifest_candidates = manifest_candidates or []
        security_report = validate_bundle_files(files)
        detection_report = audit_files(files)
        manifest_report = _manifest_permission_report(manifest_candidates)
        audit = _merge_audits(security_report, detection_report, manifest_report)
        capabilities = [
            self._capability_preview(skill_path, files)
            for skill_path in skill_paths
        ] + manifest_candidates
        payload = {
            "source_type": source_type,
            "source_ref": source_ref,
            "capabilities": capabilities,
            "files": self._file_tree(files),
            "bundle_files": self._bundle_files(files),
            "audit": audit,
        }
        job = CapabilityImportJob(
            user_id=user_id,
            source_type=source_type,
            source_ref=source_ref,
            status="previewed",
            preview_payload=payload,
            audit_summary=audit,
        )
        db.session.add(job)
        db.session.commit()
        payload["import_job_id"] = job.id
        job.preview_payload = payload
        db.session.commit()
        return payload, None

    def _capability_preview(self, skill_path, files):
        skill = next(item for item in files if item["path"] == skill_path)
        root = _skill_root(skill_path)
        related = [
            item["path"] for item in files
            if root == "" or item["path"] == skill_path or item["path"].startswith(f"{root}/")
        ]
        return {
            "type": "skill",
            "name": _title_from_markdown(skill.get("content")) or "Imported Skill",
            "description": "",
            "entry": skill_path,
            "root": root,
            "file_count": len(related),
            "files": related,
        }

    def _manifest_capability_previews(self, files):
        previews = []
        for item in files:
            path = item.get("path") or ""
            if not path.lower().endswith(".json"):
                continue
            manifest = _parse_manifest_json(item.get("content") or "")
            if not manifest:
                continue
            capabilities = manifest.get("capabilities") or []
            for index, capability in enumerate(capabilities):
                capability_type = capability.get("type")
                if capability_type not in {"skill", "mcp", "plugin"}:
                    continue
                previews.append({
                    "type": capability_type,
                    "name": capability.get("name") or "Imported Capability",
                    "description": capability.get("description") or "",
                    "entry": f"{path}#{index}",
                    "root": str(PurePosixPath(path).parent)
                    if str(PurePosixPath(path).parent) != "." else "",
                    "file_count": 1,
                    "files": [path],
                    "manifest_path": path,
                    "manifest_index": index,
                    "manifest": manifest,
                    "permissions": capability.get("permissions") or {},
                    "tools": capability.get("tools") or [],
                })
        return previews

    def _files_from_zip(self, zip_bytes):
        files = []
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                path = member.filename.replace("\\", "/").strip("/")
                if _is_ignored_import_path(path):
                    continue
                content = archive.read(member.filename).decode("utf-8", errors="replace")
                files.append({
                    "path": path,
                    "kind": _kind_for_path(path),
                    "content": content,
                    "size": len(content.encode("utf-8")),
                })
        return files

    def _files_from_directory(self, root: Path):
        files = []
        for current_root, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames
                if name.lower() not in IGNORED_IMPORT_DIRS
            ]
            for filename in filenames:
                path = Path(current_root) / filename
                rel = path.relative_to(root).as_posix()
                if _is_ignored_import_path(rel):
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                files.append({
                    "path": rel,
                    "kind": _kind_for_path(rel),
                    "content": content,
                    "size": len(content.encode("utf-8")),
                })
        return files

    def _find_skill_paths(self, paths):
        result = []
        for path in paths:
            normalized = path.replace("\\", "/").strip("/")
            if normalized == "SKILL.md" or normalized.endswith("/SKILL.md"):
                result.append(normalized)
        return sorted(result)

    def _file_tree(self, files):
        return [
            {
                "path": item["path"],
                "kind": item.get("kind") or _kind_for_path(item["path"]),
                "size": item.get("size") or len((item.get("content") or "").encode("utf-8")),
            }
            for item in sorted(files, key=lambda value: value["path"])
        ]

    def _bundle_files(self, files):
        return [
            {
                "path": item["path"],
                "kind": item.get("kind") or _kind_for_path(item["path"]),
                "content": item.get("content") or "",
                "size": item.get("size") or len((item.get("content") or "").encode("utf-8")),
                "mime_type": item.get("mime_type") or "text/plain",
            }
            for item in sorted(files, key=lambda value: value["path"])
        ]


def _merge_audits(*reports):
    risk_items = []
    blocking_items = []
    inferred_permissions = set()
    scanned_files = set()
    for report in reports:
        risk_items.extend(report.get("risk_items") or [])
        blocking_items.extend(report.get("blocking_items") or [])
        inferred_permissions.update(report.get("inferred_permissions") or [])
        scanned_files.update(report.get("scanned_files") or [])
    return {
        "risk_level": _risk_level(risk_items),
        "risk_items": risk_items,
        "blocking_items": blocking_items,
        "inferred_permissions": sorted(inferred_permissions),
        "scanned_files": sorted(scanned_files),
    }


def _manifest_permission_report(candidates):
    permissions = set()
    scanned = set()
    for candidate in candidates or []:
        scanned.update(candidate.get("files") or [])
        declared = candidate.get("permissions") or {}
        permissions.update(declared.get("required") or [])
        permissions.update(declared.get("optional") or [])
        entry = ((candidate.get("manifest") or {}).get("capabilities") or [])[
            candidate.get("manifest_index", 0)
        ].get("entry") if candidate.get("manifest") else {}
        if isinstance(entry, dict) and entry.get("command"):
            permissions.add("run_command")
    return {
        "risk_level": "low",
        "risk_items": [],
        "blocking_items": [],
        "inferred_permissions": sorted(permissions),
        "scanned_files": sorted(scanned),
    }


def _parse_manifest_json(content):
    try:
        manifest = json.loads(content or "")
    except (TypeError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("schema_version") != "weagent.capability/v1":
        return None
    if not isinstance(manifest.get("capabilities"), list):
        return None
    return manifest


def _risk_level(items):
    severities = {item.get("severity") for item in items}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _title_from_markdown(markdown):
    for line in (markdown or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _skill_root(skill_path):
    path = PurePosixPath(skill_path)
    if str(path) == "SKILL.md":
        return ""
    return str(path.parent)


def _kind_for_path(path):
    normalized = path.replace("\\", "/")
    if normalized.endswith("SKILL.md"):
        return "skill_md"
    if "/scripts/" in f"/{normalized}" or normalized.startswith("scripts/"):
        return "script"
    if "/references/" in f"/{normalized}" or normalized.startswith("references/"):
        return "reference"
    if "/templates/" in f"/{normalized}" or normalized.startswith("templates/"):
        return "template"
    if normalized.endswith("manifest.json"):
        return "manifest"
    return "reference"


def _is_ignored_import_path(path):
    parts = [
        part.lower()
        for part in PurePosixPath(path.replace("\\", "/")).parts
        if part not in {"", "."}
    ]
    return any(part in IGNORED_IMPORT_DIRS for part in parts)


capability_import_preview_service = CapabilityImportPreviewService()
