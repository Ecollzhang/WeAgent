"""WeAgent RAG 检索服务 — 配置."""
import os
from datetime import timedelta
from dotenv import load_dotenv

# 始终加载 services/rag/.env（无论从哪个目录启动）
_RAG_DIR = os.path.abspath(os.path.dirname(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_RAG_DIR, os.pardir, os.pardir))
_REPOSITORY_DIR = os.path.dirname(_BACKEND_DIR)
for _env_path in (
    os.path.join(_RAG_DIR, '.env'),
    os.path.join(_BACKEND_DIR, '.env'),
    os.path.join(_REPOSITORY_DIR, '.env'),
):
    load_dotenv(_env_path, override=False)


class Config:
    SERVICE_NAME = 'weagent-rag'
    PORT = int(os.getenv('RAG_PORT', '5104'))

    SECRET_KEY = os.getenv('SECRET_KEY', 'weagent-dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'weagent-jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    # MySQL — 独立数据库 weagent_rag（存储文档元数据、索引映射）
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'RAG_DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/weagent_rag?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

    # ── 向量数据库 (TODO: 队友接入) ──────────────────────────
    VECTOR_STORE_TYPE = os.getenv('VECTOR_STORE_TYPE', 'chromadb')
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
    CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
    MILVUS_HOST = os.getenv('MILVUS_HOST', 'localhost')
    MILVUS_PORT = int(os.getenv('MILVUS_PORT', '19530'))

    # ── 服务间认证 ──────────────────────────────────────────
    INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', os.getenv('RAG_INTERNAL_API_KEY', 'weagent-rag-internal-key'))

    # ── Embedding 模型 ──────────────────────────────────────
    EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'ollama')  # 'ollama' | 'openai'
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text:latest')
    EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY', '')
    EMBEDDING_BASE_URL = os.getenv('EMBEDDING_BASE_URL', 'http://localhost:11434')
