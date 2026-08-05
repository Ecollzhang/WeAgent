"""网页爬取和 URL 下载."""
import ipaddress
import os
import socket
import sys
import urllib.parse

import requests

_BEAUTIFULSOUP_OK = False
try:
    from bs4 import BeautifulSoup
    _BEAUTIFULSOUP_OK = True
except ImportError:
    pass

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)
TIMEOUT = (5, 15)
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_WEBPAGE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3


def _validate_public_url(url: str):
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must contain a hostname and no embedded credentials")
    addresses = socket.getaddrinfo(
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    for entry in addresses:
        address = ipaddress.ip_address(entry[4][0])
        if not address.is_global:
            raise ValueError(
                "URL resolves to a private, loopback, link-local, or reserved address"
            )
    return parsed


def _download(url: str, max_bytes: int):
    session = requests.Session()
    session.trust_env = False
    current_url = url
    try:
        for redirect_count in range(MAX_REDIRECTS + 1):
            _validate_public_url(current_url)
            response = session.get(
                current_url,
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=False,
            )
            if response.is_redirect or response.is_permanent_redirect:
                response.close()
                if redirect_count >= MAX_REDIRECTS:
                    raise ValueError("Too many HTTP redirects")
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("Redirect response is missing Location")
                current_url = urllib.parse.urljoin(current_url, location)
                continue

            response.raise_for_status()
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                response.close()
                raise ValueError("Remote content exceeds the maximum allowed size")
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    response.close()
                    raise ValueError("Remote content exceeds the maximum allowed size")
                chunks.append(chunk)
            return response, b"".join(chunks), current_url
        raise ValueError("Too many HTTP redirects")
    finally:
        session.close()


def fetch_url(url: str) -> tuple:
    """从 URL 下载文件内容.

    Returns:
        (bytes, filename, content_type)
    """
    resp, content, final_url = _download(url, MAX_DOCUMENT_BYTES)

    content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()
    # try filename from Content-Disposition
    filename = ''
    cd = resp.headers.get('Content-Disposition', '')
    if 'filename=' in cd:
        for part in cd.split(';'):
            part = part.strip()
            if part.startswith('filename='):
                filename = part.split('=', 1)[1].strip('"')
                break
    if not filename:
        filename = urllib.parse.urlparse(final_url).path.rstrip('/').rsplit('/', 1)[-1] or 'document'
    filename = os.path.basename(filename)

    return content, filename, content_type


def scrape_url(url: str) -> tuple:
    """爬取网页正文.

    Returns:
        (text: str, title: str, metadata: dict)
    """
    resp, content, final_url = _download(url, MAX_WEBPAGE_BYTES)
    content_type = resp.headers.get('Content-Type', '').split(';')[0].strip().lower()
    if content_type not in {'text/html', 'text/plain', 'application/xhtml+xml'}:
        raise ValueError(f'Unsupported webpage content type: {content_type or "missing"}')
    encoding = resp.encoding or resp.apparent_encoding or 'utf-8'
    html = content.decode(encoding, errors='replace')

    if _BEAUTIFULSOUP_OK:
        return _extract_with_bs(html, final_url)
    else:
        # fallback: strip HTML tags crudely
        import re
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip(), final_url, {'content_type': 'html', 'warning': 'BeautifulSoup not installed, crude extraction'}


def _extract_with_bs(html: str, url: str) -> tuple:
    soup = BeautifulSoup(html, 'html.parser')

    title = ''
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # remove noise elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()

    # prefer article/main content
    content = soup.find('article') or soup.find('main') or soup.find('body')
    if content:
        text = content.get_text(separator='\n', strip=True)
    else:
        text = soup.get_text(separator='\n', strip=True)

    # clean up excessive whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)

    return text, title, {
        'content_type': 'webpage',
        'source_url': url,
        'title': title,
    }
