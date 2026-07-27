"""文本分块 — 按语义边界拆分文档."""
import re
import uuid

# 默认值：每块约 800 tokens，相邻块 100 tokens 重叠
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100


def gen_chunk_id():
    return str(uuid.uuid4())


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    """将长文本拆分为可索引的块.

    策略:
    1. 按段落(连续两个换行)拆分
    2. 段落按句子拆分(中英文标点)
    3. 合并句子直到接近 chunk_size
    4. 相邻块保留 overlap 大小的重叠

    Returns:
        [{"id": str, "content": str, "chunk_index": int, "token_count": int}, ...]
    """
    paragraphs = _split_paragraphs(text)
    sentences = []
    for para in paragraphs:
        sentences.extend(_split_sentences(para))

    chunks = []
    current = []
    current_len = 0
    overlap_buffer = []

    for sent in sentences:
        sent_len = _estimate_tokens(sent)

        if current_len + sent_len > chunk_size and current:
            # store current chunk
            chunk_content = ''.join(current)
            chunks.append({
                'id': gen_chunk_id(),
                'content': chunk_content,
                'chunk_index': len(chunks),
                'token_count': _estimate_tokens(chunk_content),
            })

            # keep overlap from end of current chunk
            overlap_text = ''.join(overlap_buffer[-overlap:] if len(overlap_buffer) > overlap else overlap_buffer)
            overlap_tokens = _estimate_tokens(overlap_text)
            current = [overlap_text] if overlap_text else []
            current_len = overlap_tokens
            overlap_buffer = []

        current.append(sent)
        current_len += sent_len
        overlap_buffer.append(sent)

    # last chunk
    if current:
        chunk_content = ''.join(current)
        chunks.append({
            'id': gen_chunk_id(),
            'content': chunk_content,
            'chunk_index': len(chunks),
            'token_count': _estimate_tokens(chunk_content),
        })

    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """按段落拆分."""
    parts = re.split(r'\n\s*\n', text)
    return [p.strip() for p in parts if p.strip()]


def _split_sentences(text: str) -> list[str]:
    """按句子拆分（中英文标点）."""
    # 按句尾标点拆分，保留标点
    parts = re.split(r'(?<=[。！？.!?\n])\s*', text)
    # 合并过短的片段
    merged = []
    buf = ''
    for p in parts:
        if not p.strip():
            continue
        buf += p
        if len(buf) >= 20:  # 最小句子长度
            merged.append(buf)
            buf = ''
    if buf.strip():
        merged.append(buf)
    return merged if merged else [text]


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数量.
    中文: ~1.5 字符/token, 英文: ~4 字符/token,
    取混合估算 ~2.5 字符/token.
    """
    return max(1, len(text) // 2)
