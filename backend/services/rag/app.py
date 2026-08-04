"""WeAgent RAG 检索服务.

提供统一的文档解析、向量索引、语义检索能力，供三个领域服务调用。

启动方式:
    cd services/rag
    python app.py
"""
import sys
import os

_RAG_DIR = os.path.abspath(os.path.dirname(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_RAG_DIR, '..', '..'))
sys.path.insert(0, _RAG_DIR)
sys.path.insert(1, _BACKEND_DIR)

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import redis

from config import Config
from models.database import db

# ── 创建 Flask 应用 ──────────────────────────────────────
app = Flask(Config.SERVICE_NAME)
app.config.from_object(Config)

# 数据库 — 由 RAG models 管理的 SQLAlchemy 实例
db.init_app(app)

# JWT — 与核心服务共用同一 secret
jwt = JWTManager(app)

# CORS
CORS(app)

# Redis (可选)
try:
    redis_client = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# ── 错误处理 ──────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({'code': 400, 'error': 'Bad request', 'service': Config.SERVICE_NAME}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({'code': 404, 'error': 'Not found', 'service': Config.SERVICE_NAME}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'code': 500, 'error': 'Internal server error', 'service': Config.SERVICE_NAME}), 500

# ── 健康检查 ──────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'service': Config.SERVICE_NAME, 'status': 'ok', 'port': Config.PORT})


@app.route('/api/rag/health')
def api_health():
    """标准化健康检查端点。"""
    try:
        from models.database import db as _db
        from sqlalchemy import text as sa_text
        _db.session.execute(sa_text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "1.0.0",
        "uptime_seconds": 0,
        "dependencies": {
            "database": db_status,
        },
    })

def _build_rag_spec():
    """构建 RAG 服务的标准化 spec。"""
    return {
        "service": Config.SERVICE_NAME,
        "version": "1.0.0",
        "description": "RAG知识库检索和文档管理服务 — 提供文档解析、向量索引、语义检索能力",
        "base_url": f"http://localhost:{Config.PORT}",
        "status": "healthy",
        "capabilities": [
            {"name": "文档检索", "description": "语义搜索知识库文档，返回相关文本片段及相似度分数"},
            {"name": "混合搜索", "description": "语义+关键词混合搜索，兼顾精确匹配和语义理解"},
            {"name": "文档管理", "description": "文档上传、URL下载、网页爬取、预览、确认、重处理、删除"},
            {"name": "服务状态", "description": "检查各组件健康状态（MySQL、向量存储、嵌入服务）"},
        ],
        "popular_endpoints": [
            {"method": "POST", "path": "/api/rag/search",
             "description": "语义搜索知识库文档",
             "params": {"query": "搜索关键词", "top_k": 5, "domain": "rd/edu/office(可选)",
                        "score_threshold": 0.0, "document_ids": ["可选文档ID列表"]}},
            {"method": "POST", "path": "/api/rag/search/hybrid",
             "description": "混合搜索（语义+关键词）",
             "params": {"query": "搜索关键词", "top_k": 5, "keyword_top_k": 3, "domain": "可选"}},
            {"method": "GET",  "path": "/api/rag/documents",
             "description": "列出知识库文档",
             "params": {"page": 1, "per_page": 20, "domain": "可选", "search": "按名称搜索"}},
            {"method": "POST", "path": "/api/rag/documents/upload",
             "description": "上传文件到知识库（PDF/Word/Markdown/TXT）",
             "params": {"file": "上传的文件", "domain": "rd", "workspace_id": "可选"}},
            {"method": "POST", "path": "/api/rag/documents/fetch-url",
             "description": "从URL下载文档并导入",
             "params": {"url": "文档URL", "domain": "rd"}},
            {"method": "POST", "path": "/api/rag/documents/scrape-url",
             "description": "爬取网页内容并导入",
             "params": {"url": "网页URL", "domain": "rd"}},
            {"method": "GET",  "path": "/api/rag/status",
             "description": "检查RAG服务各组件健康状态"},
        ],
        "all_endpoints": [],
    }


@app.route('/api/rag/spec')
def api_spec():
    """返回 RAG 服务的接口描述，Agent 可通过此端点自动发现所有可用接口。"""
    return jsonify(_build_rag_spec())

# ── 注册 RAG 蓝图 ──────────────────────────────────────
from controllers.document_controller import document_bp
from controllers.search_controller import search_bp
from controllers.status_controller import status_bp

app.register_blueprint(document_bp, url_prefix='/api/rag/documents')
app.register_blueprint(search_bp, url_prefix='/api/rag')
app.register_blueprint(status_bp, url_prefix='/api/rag')

if __name__ == '__main__':
    with app.app_context():
        import models.document  # noqa: F401
        import models.chunk     # noqa: F401
        db.create_all()
    print(f'[WeAgent] RAG检索服务启动 -> http://127.0.0.1:{Config.PORT}')
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)
