"""检索 API — 语义搜索 + 混合搜索."""
from functools import wraps

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request

from config import Config
from models.document import Document
from models.chunk import Chunk
from services.embedding_service import embedding_service
from services.vector_service import vector_service

search_bp = Blueprint('rag_search', __name__)


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


def _check_internal_key():
    """检查内部 API Key."""
    api_key = Config.INTERNAL_API_KEY
    if not api_key:
        return False
    req_key = request.headers.get('X-Internal-API-Key', '')
    return req_key and req_key == api_key


def auth_optional(f):
    """支持 JWT 或内部 API Key 任一认证方式."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _check_internal_key():
            return f(*args, **kwargs)
        verify_jwt_in_request()
        return f(*args, **kwargs)
    return wrapper


@search_bp.route('/search', methods=['POST'])
@auth_optional
def semantic_search():
    """语义搜索.

    Request body:
        query: str          — 搜索文本
        domain: str         — 领域过滤（可选）
        workspace_id: str   — 工作空间过滤（可选）
        top_k: int          — 返回数量（默认 5）
        score_threshold: float — 最低相似度阈值（默认 0）
    """
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return _error('query is required')

    top_k = data.get('top_k', 5)
    score_threshold = data.get('score_threshold', 0)
    domain = data.get('domain')
    workspace_id = data.get('workspace_id')
    document_ids = data.get('document_ids')  # optional: list of document IDs to filter by

    # 构建过滤条件
    filter_meta = {}
    if domain:
        filter_meta['domain'] = domain
    if workspace_id:
        filter_meta['workspace_id'] = workspace_id
    if not filter_meta:
        filter_meta = None

    # 生成 query embedding → 搜索
    try:
        query_emb = embedding_service.embed_single(query)
    except Exception as e:
        return _error(f'Embedding failed: {e}')

    results = vector_service.search(
        query_emb, top_k=top_k, filter_meta=filter_meta,
        document_ids=document_ids if document_ids else None,
    )

    # 过滤低分结果
    if score_threshold > 0:
        results = [r for r in results if r['score'] >= score_threshold]

    # 补充文档信息
    doc_ids = list(set(r['metadata'].get('document_id', '') for r in results))
    docs_map = {}
    if doc_ids:
        docs = Document.query.filter(Document.id.in_(doc_ids)).all()
        docs_map = {d.id: d for d in docs}

    for r in results:
        doc_id = r['metadata'].get('document_id', '')
        doc = docs_map.get(doc_id)
        r['document'] = {
            'id': doc_id,
            'name': doc.name if doc else '',
            'source_type': doc.source_type if doc else '',
            'file_type': doc.file_type if doc else '',
        }

    return _ok({
        'query': query,
        'results': results,
        'total': len(results),
        'top_k': top_k,
    })


@search_bp.route('/search/hybrid', methods=['POST'])
@auth_optional
def hybrid_search():
    """混合搜索 — 语义 + 关键词.

    Request body:
        query: str          — 搜索文本
        domain: str         — 领域过滤（可选）
        workspace_id: str   — 工作空间过滤（可选）
        top_k: int          — 语义搜索返回数量（默认 5）
        keyword_top_k: int  — 关键词搜索返回数量（默认 3）
    """
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return _error('query is required')

    top_k = data.get('top_k', 5)
    keyword_top_k = data.get('keyword_top_k', 3)
    domain = data.get('domain')
    workspace_id = data.get('workspace_id')

    # ── 语义搜索 ──
    filter_meta = {}
    if domain:
        filter_meta['domain'] = domain
    if workspace_id:
        filter_meta['workspace_id'] = workspace_id
    if not filter_meta:
        filter_meta = None

    try:
        query_emb = embedding_service.embed_single(query)
    except Exception as e:
        return _error(f'Embedding failed: {e}')

    semantic_results = vector_service.search(query_emb, top_k=top_k, filter_meta=filter_meta)

    # ── 关键词搜索（MySQL LIKE） ──
    keyword_chunks = []
    if keyword_top_k > 0:
        kq = Chunk.query.filter(
            Chunk.content.contains(query)
        ).limit(keyword_top_k).all()
        for c in kq:
            keyword_chunks.append({
                'chunk_id': c.vector_id,
                'content': c.content[:500],
                'score': 1.0,
                'source': 'keyword',
                'metadata': {
                    'document_id': c.document_id,
                    'chunk_index': c.chunk_index,
                },
            })

    # ── 去重合并 ──
    seen_ids = set()
    merged = []
    for r in semantic_results:
        cid = r['chunk_id']
        if cid not in seen_ids:
            seen_ids.add(cid)
            r['source'] = 'semantic'
            merged.append(r)
    for r in keyword_chunks:
        cid = r['chunk_id']
        if cid not in seen_ids:
            seen_ids.add(cid)
            merged.append(r)

    # 补充文档信息
    doc_ids = list(set(r['metadata'].get('document_id', '') for r in merged))
    docs_map = {}
    if doc_ids:
        docs = Document.query.filter(Document.id.in_(doc_ids)).all()
        docs_map = {d.id: d for d in docs}

    for r in merged:
        doc_id = r['metadata'].get('document_id', '')
        doc = docs_map.get(doc_id)
        r['document'] = {
            'id': doc_id,
            'name': doc.name if doc else '',
            'source_type': doc.source_type if doc else '',
            'file_type': doc.file_type if doc else '',
        }

    return _ok({
        'query': query,
        'results': merged,
        'total': len(merged),
        'semantic_count': len(semantic_results),
        'keyword_count': len(keyword_chunks),
    })
