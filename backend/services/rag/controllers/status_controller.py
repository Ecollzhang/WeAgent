"""服务状态 API — 检查各组件是否正常."""
from flask import Blueprint, jsonify
from sqlalchemy import text

from models.database import db
from services.embedding_service import embedding_service
from services.vector_service import vector_service

status_bp = Blueprint('rag_status', __name__)


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


@status_bp.route('/status', methods=['GET'])
def service_status():
    """返回 RAG 服务各组件的状态."""
    components = {}

    # 检查数据库
    try:
        db.session.execute(text('SELECT 1'))
        components['mysql'] = 'ok'
    except Exception as e:
        components['mysql'] = f'error: {e}'

    # 检查向量存储
    try:
        count = vector_service.count()
        components['vector_store'] = f'ok ({count} vectors)'
    except Exception as e:
        components['vector_store'] = f'error: {e}'

    # 检查 Embedding 服务
    if not embedding_service.configured:
        components['embedding'] = 'not_configured'
    else:
        try:
            dim = embedding_service.dimension
            components['embedding'] = f'ok (provider: {embedding_service.provider}, model: {embedding_service.model}, dim: {dim})'
        except Exception as e:
            components['embedding'] = f'error: {e}'

    all_ok = all(
        not str(v).startswith('error') and v != 'not_configured'
        for v in components.values()
    )

    return _ok({
        'status': 'healthy' if all_ok else 'degraded',
        'components': components,
    })
