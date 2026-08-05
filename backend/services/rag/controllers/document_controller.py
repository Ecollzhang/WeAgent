"""文档管理 API — 上传、下载、爬取、预览、确认、删除、列表."""
import os
import tempfile
import uuid
import sys
import threading
from functools import wraps

from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from sqlalchemy.orm.attributes import flag_modified

from models.database import db
from models.document import Document
from models.chunk import Chunk
from utils.parser import extract_text, detect_file_type
from utils.scraper import fetch_url, scrape_url
from services.chunker import chunk_text
from services.embedding_service import embedding_service
from services.vector_service import vector_service
from access_scope import resolve_search_scope
from config import Config

document_bp = Blueprint('rag_documents', __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_user_id():
    scope = getattr(g, "rag_document_scope", None)
    return scope.user_id if scope else get_jwt_identity()


def _check_internal_key():
    key = str(getattr(Config, "INTERNAL_API_KEY", "") or "")
    return bool(key) and request.headers.get("X-Internal-API-Key", "") == key


def document_auth_scoped(handler):
    """Authenticate user document calls or a server-issued internal scope."""

    @wraps(handler)
    def wrapped(*args, **kwargs):
        internal = _check_internal_key()
        identity = None
        if not internal:
            verify_jwt_in_request()
            identity = get_jwt_identity()
        payload = (
            dict(request.form)
            if request.form
            else request.get_json(silent=True) or {}
        )
        try:
            scope = resolve_search_scope(
                internal=internal,
                headers=request.headers,
                payload=payload,
                jwt_identity=identity,
            )
        except PermissionError as exc:
            return _error(str(exc), 403)
        if not internal and scope.domain == "edu":
            return _error(
                "Education documents must be ingested through the Education service",
                403,
            )
        g.rag_document_scope = scope
        return handler(*args, **kwargs)

    return wrapped


def _scoped_document(doc_id):
    scope = getattr(g, "rag_document_scope", None)
    query = Document.query.filter_by(id=doc_id)
    if scope:
        query = query.filter_by(user_id=scope.user_id, domain=scope.domain)
        if scope.internal and scope.workspace_id:
            query = query.filter_by(workspace_id=scope.workspace_id)
    else:
        query = query.filter_by(user_id=get_jwt_identity())
    return query.first()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


# ── 上传文件 ────────────────────────────────────────────

@document_bp.route('/upload', methods=['POST'])
@document_auth_scoped
def upload_document():
    """上传文档文件."""
    user_id = _get_user_id()

    if 'file' not in request.files:
        return _error('No file provided')

    file = request.files['file']
    if not file.filename:
        return _error('Empty filename')

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return _error(f'File too large, max {MAX_FILE_SIZE // (1024*1024)}MB')

    scope = g.rag_document_scope
    domain = scope.domain
    workspace_id = scope.workspace_id

    _ensure_upload_dir()
    saved_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(save_path, 'wb') as f:
        f.write(file_bytes)

    file_type = detect_file_type(file.filename)

    doc = Document(
        user_id=user_id,
        workspace_id=workspace_id,
        domain=domain,
        name=file.filename,
        source_type='upload',
        file_type=file_type,
        file_size=len(file_bytes),
        status='pending',
    )
    db.session.add(doc)
    db.session.commit()

    # 同步解析文本
    try:
        text, page_count, meta = extract_text(file_bytes, file.filename)
    except Exception as e:
        doc.status = 'error'
        doc.extra_meta = {'error': str(e)}
        db.session.commit()
        return _error(f'Failed to parse document: {e}')

    trusted_meta = {}
    if scope.internal and domain == "edu":
        visibility = request.headers.get("X-WeAgent-Visibility", "")
        if visibility not in {"course_teacher", "course_published"}:
            doc.status = "error"
            db.session.commit()
            return _error("Invalid Education document visibility", 403)
        trusted_meta = {
            "visibility_scope": visibility,
            "education_resource_id": request.headers.get(
                "X-WeAgent-Resource-ID", ""
            )[:100],
        }
    doc.extra_meta = {
        **meta,
        **trusted_meta,
        'page_count': page_count,
        'text_length': len(text),
        '_text': text,
    }
    db.session.commit()

    return _ok({
        'id': doc.id,
        'name': doc.name,
        'file_type': file_type,
        'file_size': len(file_bytes),
        'text_length': len(text),
        'page_count': page_count,
    }, 'Document uploaded, awaiting confirmation', 201)


# ── 从 URL 下载 ──────────────────────────────────────────

@document_bp.route('/fetch-url', methods=['POST'])
@jwt_required()
def fetch_from_url():
    """从 URL 下载文档."""
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return _error('url is required')

    user_id = _get_user_id()
    domain = data.get('domain', 'rd')
    workspace_id = data.get('workspace_id') or None

    try:
        content, filename, content_type = fetch_url(url)
    except Exception as e:
        return _error(f'Failed to download: {e}')

    file_type = detect_file_type(filename)
    if file_type == 'unknown' and 'pdf' in content_type:
        file_type = 'pdf'
    elif file_type == 'unknown' and 'word' in content_type:
        file_type = 'docx'

    try:
        text, page_count, meta = extract_text(content, filename)
    except Exception as e:
        return _error(f'Failed to parse document: {e}')

    doc = Document(
        user_id=user_id,
        workspace_id=workspace_id,
        domain=domain,
        name=filename,
        source_type='url',
        source_url=url,
        file_type=file_type,
        file_size=len(content),
        status='pending',
        extra_meta={**meta, 'page_count': page_count, 'text_length': len(text), '_text': text},
    )
    db.session.add(doc)
    db.session.commit()

    return _ok({
        'id': doc.id,
        'name': doc.name,
        'file_type': file_type,
        'file_size': len(content),
        'text_length': len(text),
        'page_count': page_count,
    }, 'Document fetched, awaiting confirmation', 201)


# ── 爬取网页 ────────────────────────────────────────────

@document_bp.route('/scrape-url', methods=['POST'])
@jwt_required()
def scrape_from_url():
    """爬取网页内容."""
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return _error('url is required')

    user_id = _get_user_id()
    domain = data.get('domain', 'rd')
    workspace_id = data.get('workspace_id') or None

    try:
        text, title, meta = scrape_url(url)
    except Exception as e:
        return _error(f'Failed to scrape: {e}')

    name = (title or url.rsplit('/', 1)[-1] or 'webpage') + '.html'

    doc = Document(
        user_id=user_id,
        workspace_id=workspace_id,
        domain=domain,
        name=name,
        source_type='scrape',
        source_url=url,
        file_type='html',
        file_size=len(text.encode('utf-8')),
        status='pending',
        extra_meta={**meta, 'text_length': len(text), '_text': text},
    )
    db.session.add(doc)
    db.session.commit()

    return _ok({
        'id': doc.id,
        'name': doc.name,
        'file_type': 'html',
        'text_length': len(text),
        'title': title,
    }, 'Webpage scraped, awaiting confirmation', 201)


# ── 预览 ────────────────────────────────────────────────

@document_bp.route('/<doc_id>/preview', methods=['GET'])
@jwt_required()
def preview_document(doc_id):
    """预览文档解析内容（前 2000 字）."""
    doc = Document.query.get(doc_id)
    if not doc:
        return _error('Document not found', 404)

    text = (doc.extra_meta or {}).get('_text', '')
    preview_len = min(len(text), 2000)

    return _ok({
        'id': doc.id,
        'name': doc.name,
        'source_type': doc.source_type,
        'file_type': doc.file_type,
        'file_size': doc.file_size,
        'domain': doc.domain,
        'text_length': len(text),
        'page_count': (doc.extra_meta or {}).get('page_count', 1),
        'title': (doc.extra_meta or {}).get('title', ''),
        'preview': text[:preview_len],
        'has_more': len(text) > 2000,
        'status': doc.status,
    })


# ── 后台文档处理 ──────────────────────────────────────────

def _process_document_bg(app, doc_id, text, doc_name, doc_domain, workspace_id):
    """后台线程：分块 → 向量化 → 入库."""
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc:
            return
        try:
            # 分块
            chunks_data = chunk_text(text)
            if not chunks_data:
                doc.status = 'error'
                doc.extra_meta = {**(doc.extra_meta or {}), 'error': 'Chunking produced no chunks'}
                flag_modified(doc, 'extra_meta')
                db.session.commit()
                return

            # 生成 embeddings
            chunk_texts = [c['content'] for c in chunks_data]
            try:
                embeddings = embedding_service.embed(chunk_texts)
            except Exception as e:
                doc.status = 'error'
                doc.extra_meta = {**(doc.extra_meta or {}), 'error': f'Embedding failed: {e}'}
                flag_modified(doc, 'extra_meta')
                db.session.commit()
                return

            # 写入 ChromaDB
            vector_ids = []
            vector_docs = []
            vector_embs = []
            vector_metas = []
            for i, c in enumerate(chunks_data):
                vid = f"{doc.id}_{c['chunk_index']}"
                vector_ids.append(vid)
                vector_docs.append(c['content'])
                vector_embs.append(embeddings[i])
                vector_metas.append({
                    'document_id': doc.id,
                    'document_name': doc_name,
                    'chunk_index': c['chunk_index'],
                    'domain': doc_domain,
                    'workspace_id': workspace_id or '',
                    'user_id': doc.user_id,
                    'visibility_scope': (
                        (doc.extra_meta or {}).get('visibility_scope') or ''
                    ),
                })
            vector_service.add(vector_ids, vector_embs, vector_docs, vector_metas)

            # 写入 MySQL chunks
            total_tokens = 0
            for i, c in enumerate(chunks_data):
                chunk = Chunk(
                    document_id=doc.id,
                    chunk_index=c['chunk_index'],
                    content=c['content'],
                    token_count=c['token_count'],
                    vector_id=vector_ids[i],
                )
                db.session.add(chunk)
                total_tokens += c['token_count']

            doc.chunk_count = len(chunks_data)
            doc.total_tokens = total_tokens
            doc.status = 'ready'
            db.session.commit()

        except Exception as e:
            doc.status = 'error'
            doc.extra_meta = {**(doc.extra_meta or {}), 'error': str(e)}
            flag_modified(doc, 'extra_meta')
            db.session.commit()


# ── 确认存储（分块 + 向量化）─────────────────────────────

@document_bp.route('/<doc_id>/confirm', methods=['POST'])
@document_auth_scoped
def confirm_document(doc_id):
    """确认存储文档 — 启动后台处理，立即返回."""
    doc = _scoped_document(doc_id)
    if not doc:
        return _error('Document not found', 404)
    if doc.status == 'ready':
        return _error('Document already confirmed')
    if doc.status == 'processing':
        return _error('Document is already being processed')

    text = (doc.extra_meta or {}).pop('_text', '')
    if not text:
        return _error('No text content to process')

    doc.status = 'processing'
    flag_modified(doc, 'extra_meta')
    db.session.commit()

    # Extract metadata before starting thread
    doc_name = doc.name
    doc_domain = doc.domain
    ws_id = doc.workspace_id
    app = current_app._get_current_object()

    thread = threading.Thread(
        target=_process_document_bg,
        args=(app, doc.id, text, doc_name, doc_domain, ws_id),
        daemon=True,
    )
    thread.start()

    return _ok({
        'id': doc.id,
        'status': 'processing',
        'text_length': len(text),
    }, 'Document processing started in background')


# ── 重新处理 ──────────────────────────────────────────────

@document_bp.route('/<doc_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_document(doc_id):
    """重新解析并处理文档（用于 error 状态的文档重试）."""
    doc = Document.query.get(doc_id)
    if not doc:
        return _error('Document not found', 404)

    if doc.source_type == 'upload':
        return _error('Upload documents cannot be re-processed automatically, please re-upload')

    # Clear existing chunks and vectors
    if doc.chunk_count:
        try:
            vector_ids = [f"{doc.id}_{i}" for i in range(doc.chunk_count)]
            vector_service.delete_by_ids(vector_ids)
        except Exception:
            pass
        Chunk.query.filter_by(document_id=doc.id).delete()

    doc.status = 'processing'
    doc.chunk_count = 0
    doc.total_tokens = 0
    doc.extra_meta = {}
    db.session.commit()

    try:
        if doc.source_type == 'url':
            content, filename, content_type = fetch_url(doc.source_url)
        elif doc.source_type == 'scrape':
            text, title, meta = scrape_url(doc.source_url)
            content = text.encode('utf-8')
            filename = doc.name
        else:
            doc.status = 'error'
            doc.extra_meta = {'error': 'Unknown source type for re-processing'}
            db.session.commit()
            return _error('Unknown source type')

        text, page_count, meta = extract_text(content, filename)
        doc.extra_meta = {**meta, 'page_count': page_count, 'text_length': len(text), '_text': text}
        db.session.commit()

        # Chunk and index
        chunks_data = chunk_text(text)
        if not chunks_data:
            doc.status = 'error'
            doc.extra_meta = {**(doc.extra_meta or {}), 'error': 'Chunking produced no chunks'}
            db.session.commit()
            return _error('Chunking failed')

        chunk_texts = [c['content'] for c in chunks_data]
        try:
            embeddings = embedding_service.embed(chunk_texts)
        except Exception as e:
            doc.status = 'error'
            db.session.commit()
            return _error(f'Embedding failed: {e}')

        vector_ids = []
        vector_docs = []
        vector_embs = []
        vector_metas = []
        for i, c in enumerate(chunks_data):
            vid = f"{doc.id}_{c['chunk_index']}"
            vector_ids.append(vid)
            vector_docs.append(c['content'])
            vector_embs.append(embeddings[i])
            vector_metas.append({
                'document_id': doc.id,
                'document_name': doc.name,
                'chunk_index': c['chunk_index'],
                'domain': doc.domain,
                'workspace_id': doc.workspace_id or '',
                'user_id': doc.user_id,
            })
        vector_service.add(vector_ids, vector_embs, vector_docs, vector_metas)

        total_tokens = 0
        for i, c in enumerate(chunks_data):
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=c['chunk_index'],
                content=c['content'],
                token_count=c['token_count'],
                vector_id=vector_ids[i],
            )
            db.session.add(chunk)
            total_tokens += c['token_count']

        doc.chunk_count = len(chunks_data)
        doc.total_tokens = total_tokens
        doc.status = 'ready'
        db.session.commit()

        return _ok({
            'id': doc.id,
            'chunk_count': len(chunks_data),
            'total_tokens': total_tokens,
            'status': 'ready',
        }, 'Document re-processed successfully')

    except Exception as e:
        doc.status = 'error'
        doc.extra_meta = {**(doc.extra_meta or {}), 'error': str(e)}
        db.session.commit()
        return _error(f'Re-processing failed: {e}')


# ── 删除 ────────────────────────────────────────────────

@document_bp.route('/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """删除文档及所有分块和向量."""
    doc = Document.query.get(doc_id)
    if not doc:
        return _error('Document not found', 404)

    # 删除 ChromaDB 向量
    vector_ids = [f"{doc.id}_{i}" for i in range(max(1, doc.chunk_count))]
    try:
        vector_service.delete_by_ids(vector_ids)
    except Exception:
        pass

    # 级联删除 MySQL chunks + document
    db.session.delete(doc)
    db.session.commit()

    return _ok({'id': doc_id}, 'Document deleted')


# ── 列表查询 ────────────────────────────────────────────

@document_bp.route('', methods=['GET'])
@jwt_required()
def list_documents():
    """文档列表，支持分页、按领域筛选、搜索."""
    user_id = _get_user_id()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    domain = request.args.get('domain')
    workspace_id = request.args.get('workspace_id')
    search = request.args.get('search')

    q = Document.query.filter_by(user_id=user_id)
    if domain:
        q = q.filter_by(domain=domain)
    if workspace_id:
        q = q.filter_by(workspace_id=workspace_id)
    if search:
        q = q.filter(
            db.or_(
                Document.name.ilike(f'%{search}%'),
                Document.description.ilike(f'%{search}%'),
            )
        )

    q = q.order_by(Document.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return _ok({
        'items': [d.to_dict() for d in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


# ── 详情 ────────────────────────────────────────────────

@document_bp.route('/<doc_id>', methods=['GET'])
@document_auth_scoped
def get_document(doc_id):
    """文档详情（含分块列表）."""
    doc = _scoped_document(doc_id)
    if not doc:
        return _error('Document not found', 404)
    return _ok(doc.to_dict(include_chunks=True))
