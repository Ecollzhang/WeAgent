"""网页爬取和 URL 下载."""
import sys
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
TIMEOUT = 30


def fetch_url(url: str) -> tuple:
    """从 URL 下载文件内容.

    Returns:
        (bytes, filename, content_type)
    """
    resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=TIMEOUT, stream=True)
    resp.raise_for_status()

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
        filename = url.rstrip('/').rsplit('/', 1)[-1] or 'document'

    return resp.content, filename, content_type


def scrape_url(url: str) -> tuple:
    """爬取网页正文.

    Returns:
        (text: str, title: str, metadata: dict)
    """
    resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or 'utf-8'
    html = resp.text

    if _BEAUTIFULSOUP_OK:
        return _extract_with_bs(html, url)
    else:
        # fallback: strip HTML tags crudely
        import re
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip(), url, {'content_type': 'html', 'warning': 'BeautifulSoup not installed, crude extraction'}


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
