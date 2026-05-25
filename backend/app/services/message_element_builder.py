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

    clean_path = path.lstrip('/')
    if clean_path.startswith('workspace/'):
        clean_path = clean_path[len('workspace/'):]

    name = os.path.basename(clean_path) or clean_path
    url_path = clean_path.replace('\\', '/')
    url = f'/api/sandbox/sessions/{session_id}/workspace/{url_path}'
    ext = os.path.splitext(name)[1].lower()

    if ext in IMAGE_EXTS:
        return {
            'type': 'image',
            'content': url,
            'data': {
                'url': url,
                'alt': name,
                'path': f'/workspace/{clean_path}',
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
        },
    }


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
