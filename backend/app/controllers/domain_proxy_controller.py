"""Domain Proxy — API 网关，将 /api/domain/{domain}/* 转发到对应的领域服务."""
from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required
import requests

domain_proxy_bp = Blueprint('domain_proxy', __name__)

# 领域服务端口映射
DOMAIN_SERVICE_PORTS = {
    'rd': 5101,
    'edu': 5102,
    'office': 5103,
    'rag': 5104,
}

# 代理超时（秒）
PROXY_TIMEOUT = 30


def _domain_is_enabled(domain):
    """Read the operator-controlled domain gate."""
    if domain != 'edu':
        return True

    from app.models.grayscale_config import GrayscaleConfig

    feature = GrayscaleConfig.query.filter_by(
        config_key='feature.education.enabled',
        domain='edu',
    ).first()
    return feature is None or bool(feature.enabled)


def _proxy_request(domain, path):
    """将当前请求转发到领域服务并返回响应."""
    port = DOMAIN_SERVICE_PORTS.get(domain)
    if not port:
        return None

    # 如果请求体是 multipart/form-data，直接透传 files + data
    if request.content_type and 'multipart/form-data' in request.content_type:
        return _proxy_multipart(domain, path, port)

    target_url = f'http://127.0.0.1:{port}/api/{domain}/{path}'

    # 透传 headers（排除 host）
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            timeout=PROXY_TIMEOUT,
        )
    except requests.ConnectionError:
        return None
    except requests.Timeout:
        return None

    # 透传响应
    excluded = ('content-encoding', 'content-length', 'transfer-encoding', 'connection')
    response_headers = [
        (k, v) for k, v in resp.raw.headers.items()
        if k.lower() not in excluded
    ]

    return Response(
        resp.content,
        status=resp.status_code,
        headers=response_headers,
    )


def _proxy_multipart(domain, path, port):
    """转发 multipart/form-data 请求."""
    target_url = f'http://127.0.0.1:{port}/api/{domain}/{path}'

    headers = {k: v for k, v in request.headers if k.lower() not in ('host', 'content-type')}

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            files={k: (v.filename, v.stream, v.content_type) for k, v in request.files.items()},
            data=request.form,
            timeout=PROXY_TIMEOUT,
        )
    except requests.ConnectionError:
        return None
    except requests.Timeout:
        return None

    excluded = ('content-encoding', 'content-length', 'transfer-encoding', 'connection')
    response_headers = [
        (k, v) for k, v in resp.raw.headers.items()
        if k.lower() not in excluded
    ]

    return Response(
        resp.content,
        status=resp.status_code,
        headers=response_headers,
    )


@domain_proxy_bp.route('/api/domain/<domain>/health', methods=['GET'])
def proxy_health(domain):
    """健康检查 — 不需要 JWT，直接转发."""
    path = 'health'
    resp = _proxy_request(domain, path)
    if resp is None:
        from app.utils.response import error_response
        return error_response(f'Domain service `{domain}` is unreachable', code=502)
    return resp


@domain_proxy_bp.route('/api/domain/<domain>/<path:subpath>', methods=[
    'GET', 'POST', 'PUT', 'DELETE', 'PATCH',
])
@jwt_required()
def proxy_domain_request(domain, subpath):
    """将 /api/domain/{domain}/* 请求转发到领域服务."""
    if not _domain_is_enabled(domain):
        from app.utils.response import error_response
        return error_response('Education feature is disabled', code=404)

    resp = _proxy_request(domain, subpath)
    if resp is None:
        from app.utils.response import error_response
        return error_response(f'Domain service `{domain}` is unreachable', code=502)
    return resp
