import difflib
import hashlib
import json
import posixpath
from dataclasses import dataclass
from typing import Optional


TEXT_EXTENSIONS = {
    '.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue',
    '.py', '.md', '.txt', '.json', '.xml', '.yaml', '.yml', '.toml',
    '.sql', '.csv', '.java', '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp',
    '.cs', '.go', '.rs', '.php', '.rb', '.sh', '.bat', '.ps1', '.kt', '.swift', '.dart',
}
HISTORY_ROOT = '/workspace/.weagent_history'
DIFF_PREVIEW_LINE_LIMIT = 240
AFTER_PREVIEW_CHAR_LIMIT = 12000


@dataclass
class DiffArtifact:
    path: str
    before: str
    after: str
    diff_text: str
    additions: int
    deletions: int
    applied: bool = True

    def to_element(self):
        filename = posixpath.basename(self.path) or self.path
        before_preview = self.before[:AFTER_PREVIEW_CHAR_LIMIT]
        after_preview = self.after[:AFTER_PREVIEW_CHAR_LIMIT]
        diff_preview = _trim_diff_preview(self.diff_text)
        return {
            'type': 'diff',
            'content': diff_preview,
            'status': 'done',
            'data': {
                'title': f'{filename} 变更',
                'filename': filename,
                'path': self.path,
                'language': _language_for_path(self.path),
                'before': self.before,
                'before_preview': before_preview,
                'after': self.after,
                'after_preview': after_preview,
                'diff_text': diff_preview,
                'diff_stat': {
                    'additions': self.additions,
                    'deletions': self.deletions,
                },
                'applied': self.applied,
            },
        }


class WorkspaceDiffService:
    def is_trackable(self, path: str) -> bool:
        return _is_trackable_path(path)

    def build_diff_for_write(self, mgr, session_id: str, path: str, after_bytes: bytes) -> Optional[DiffArtifact]:
        normalized_path = _normalize_workspace_path(path)
        if not normalized_path or not self.is_trackable(normalized_path):
            return None

        after_text = _decode_text(after_bytes)
        before_text = self._read_current_text(mgr, session_id, normalized_path)
        if before_text is None or before_text == after_text:
            return None
        return _build_diff_artifact(normalized_path, before_text, after_text)

    def store_snapshot_for_write(self, mgr, session_id: str, path: str, content_bytes: bytes):
        normalized_path = _normalize_workspace_path(path)
        if not normalized_path or not self.is_trackable(normalized_path):
            return
        self._store_snapshot(mgr, session_id, normalized_path, _decode_text(content_bytes))

    def capture_diff_after_write_event(self, mgr, session_id: str, path: str) -> Optional[DiffArtifact]:
        normalized_path = _normalize_workspace_path(path)
        if not normalized_path or not self.is_trackable(normalized_path):
            return None

        current_text = self._read_current_text(mgr, session_id, normalized_path)
        if current_text is None:
            return None

        latest_text = self._read_snapshot(mgr, session_id, normalized_path, 'latest')
        if latest_text == current_text:
            return None

        self._store_snapshot(mgr, session_id, normalized_path, current_text)
        if latest_text is None:
            return None
        return _build_diff_artifact(normalized_path, latest_text, current_text)

    def _read_current_text(self, mgr, session_id: str, path: str) -> Optional[str]:
        try:
            content_bytes, _ = mgr.get_raw_file(session_id, path)
        except Exception:
            return None
        return _decode_text(content_bytes)

    def _entry_dir(self, path: str) -> str:
        digest = hashlib.sha1(path.encode('utf-8')).hexdigest()
        return posixpath.join(HISTORY_ROOT, digest)

    def _snapshot_path(self, path: str, slot: str) -> str:
        return posixpath.join(self._entry_dir(path), f'{slot}.txt')

    def _meta_path(self, path: str) -> str:
        return posixpath.join(self._entry_dir(path), 'meta.json')

    def _read_snapshot(self, mgr, session_id: str, path: str, slot: str) -> Optional[str]:
        try:
            content_bytes, _ = mgr.get_raw_file(session_id, self._snapshot_path(path, slot))
        except Exception:
            return None
        return _decode_text(content_bytes)

    def _store_snapshot(self, mgr, session_id: str, path: str, content: str):
        latest_text = self._read_snapshot(mgr, session_id, path, 'latest')
        if latest_text == content:
            return

        latest_path = self._snapshot_path(path, 'latest')
        previous_path = self._snapshot_path(path, 'previous')

        if latest_text is not None:
            mgr.write_workspace_file(session_id, previous_path, latest_text.encode('utf-8'))
        mgr.write_workspace_file(session_id, latest_path, content.encode('utf-8'))

        meta = {
            'path': path,
            'language': _language_for_path(path),
        }
        mgr.write_workspace_file(
            session_id,
            self._meta_path(path),
            json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
        )


def _normalize_workspace_path(path: str) -> str:
    text = str(path or '').replace('\\', '/').strip()
    if not text:
        return ''
    if not text.startswith('/workspace/'):
        if text.startswith('workspace/'):
            text = '/' + text
        else:
            text = '/workspace/' + text.lstrip('/')
    return text


def _is_trackable_path(path: str) -> bool:
    if path.startswith(HISTORY_ROOT + '/'):
        return False
    ext = posixpath.splitext(path)[1].lower()
    return ext in TEXT_EXTENSIONS


def _decode_text(content_bytes: bytes) -> str:
    if content_bytes is None:
        return ''
    return content_bytes.decode('utf-8', errors='replace')


def _build_diff_artifact(path: str, before: str, after: str) -> DiffArtifact:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=path,
        tofile=path,
        lineterm='',
        n=3,
    ))
    diff_text = '\n'.join(diff_lines)
    additions = 0
    deletions = 0
    for line in diff_lines:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        if line.startswith('+'):
            additions += 1
        elif line.startswith('-'):
            deletions += 1
    return DiffArtifact(
        path=path,
        before=before,
        after=after,
        diff_text=diff_text,
        additions=additions,
        deletions=deletions,
    )


def _trim_diff_preview(diff_text: str) -> str:
    lines = diff_text.splitlines()
    if len(lines) <= DIFF_PREVIEW_LINE_LIMIT:
        return diff_text
    kept = lines[:DIFF_PREVIEW_LINE_LIMIT]
    kept.append(f'... diff truncated, total lines: {len(lines)}')
    return '\n'.join(kept)


def _language_for_path(path: str) -> str:
    ext = posixpath.splitext(path)[1].lower()
    return {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.css': 'css',
        '.scss': 'scss',
        '.html': 'html',
        '.htm': 'html',
        '.vue': 'vue',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.csv': 'csv',
        '.java': 'java',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.sh': 'shell',
        '.bat': 'shell',
        '.ps1': 'powershell',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.dart': 'dart',
    }.get(ext, ext.lstrip('.') or 'text')


workspace_diff_service = WorkspaceDiffService()
