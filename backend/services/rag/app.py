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
