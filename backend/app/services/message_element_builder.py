import os
import re


CODE_FENCE_RE = re.compile(r'```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```')
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
WORKSPACE_FILE_RE = re.compile(
    r'/?workspace/[^\s`\'")\]，。；;]+?\.(?:png|jpe?g|gif|webp|svg|bmp|md|txt|html?|css|js|json|py|pdf|csv|xml|vue)',
    re.IGNORECASE,
)


def build_summary_elements(raw_output, fallback='正在处理...'):
    """Build lightweight display elements while keeping raw output separate."""
    text = (raw_output or '').strip()
    if not text:
        return [{'type': 'text', 'data': {'content': fallback}}]

    summary = text[-1200:]
    elements = [{'type': 'text', 'data': {'content': summary}}]

    for match in CODE_FENCE_RE.finditer(text):
        language = match.group(1) or 'text'
        content = match.group(2)
        if content.strip():
            elements.append({
                'type': 'code',
                'data': {
                    'language': language,
                    'content': content.strip(),
                },
            })

    return elements


def file_event_element(session_id, file_data):
    path = (file_data or {}).get('file') or ''
    if not path:
        return None

    normalized_path = _normalize_workspace_event_path(path)
    if not normalized_path:
        return None

    clean_path = normalized_path.lstrip('/')
    if clean_path.startswith('workspace/'):
        clean_path = clean_path[len('workspace/'):]

    name = os.path.basename(clean_path) or clean_path
    if name.startswith('.'):
        return None
    url_path = clean_path.replace('\\', '/')
    url = f'/api/sandbox/sessions/{session_id}/workspace/{url_path}'
    ext = os.path.splitext(name)[1].lower()
    workspace_name = _workspace_name_from_clean_path(clean_path)
    agent_meta = {'workspace_name': workspace_name} if workspace_name else {}

    if ext in IMAGE_EXTS:
        return {
            'type': 'image',
            'content': url,
            'data': {
                'url': url,
                'alt': name,
                'path': f'/workspace/{clean_path}',
                **agent_meta,
            },
        }

    return {
        'type': 'file',
        'content': name,
        'data': {
            'name': name,
            'url': url,
            'size': (file_data or {}).get('size'),
            'path': f'/workspace/{clean_path}',
            **agent_meta,
        },
    }


def report_event_element(session_id, report):
    if not isinstance(report, dict):
        return None

    element_type = report.get('type') or 'text'
    data = dict(report.get('data') or {})
    content = report.get('content', '')
    title = data.get('title') or report.get('title') or ''

    if element_type in {'file', 'image'}:
        path = data.get('path') or content
        if not path:
            return None
        element = file_event_element(session_id, {
            'file': path,
            'size': data.get('size'),
        })
        if not element:
            return None
        element['status'] = report.get('status')
        if report.get('step_id'):
            element['step_id'] = report.get('step_id')
            element.setdefault('data', {})['step_id'] = report.get('step_id')
        if title:
            element.setdefault('data', {})['title'] = title
        if content:
            element['content'] = content
        return element

    element = {
        'type': element_type,
        'content': content,
        'status': report.get('status'),
        'data': {
            **data,
            'title': title,
        },
    }
    if report.get('step_id'):
        element['step_id'] = report.get('step_id')
        element['data']['step_id'] = report.get('step_id')
    return element


def mentioned_file_elements(session_id, text):
    """Build file/image elements for workspace paths mentioned in text."""
    if not session_id or not text:
        return []

    elements = []
    seen = set()
    for match in WORKSPACE_FILE_RE.findall(text):
        path = '/' + match.lstrip('/').replace('\\', '/')
        path = path.rstrip('.,;:，。；：')
        if path in seen:
            continue
        seen.add(path)
        element = file_event_element(session_id, {'file': path, 'size': None})
        if element:
            elements.append(element)
    return elements


def _normalize_workspace_event_path(path):
    normalized_path = str(path or '').replace('\\', '/').strip()
    if not normalized_path:
        return ''
    if normalized_path.startswith('/workspace/'):
        return normalized_path
    if normalized_path.startswith('workspace/'):
        return '/' + normalized_path
    if normalized_path.startswith('/agents/') or normalized_path.startswith('agents/'):
        return '/workspace/' + normalized_path.lstrip('/')
    return ''


def _workspace_name_from_clean_path(clean_path):
    parts = [part for part in str(clean_path or '').split('/') if part]
    if len(parts) >= 3 and parts[0] == 'agents':
        return parts[1]
    return ''


def text_delta_element(chunk):
    return {
        'type': 'text',
        'content': chunk or '',
    }


def progress_element(title, status='running', detail=None):
    return {
        'type': 'progress',
        'content': title or '',
        'status': status,
        'detail': detail,
    }


def result_element(title, content='', detail=None):
    return {
        'type': 'result',
        'content': content or title or '',
        'data': {
            'title': title or '执行结果',
            'content': content or '',
            **(detail or {}),
        },
    }
