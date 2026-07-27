"""领域服务基座。

提供统一的 Flask 应用初始化、JWT 验证、错误处理、健康检查。
每个领域服务通过继承此基座快速启动一个与核心服务鉴权互通的后端。

使用方式:
    from weagent_core.services.domain_base import DomainServiceBase
    from config import Config

    service = DomainServiceBase(Config)
    app = service.app
    db = service.db

    # 注册领域专属蓝图
    from controllers.xxx_controller import xxx_bp
    app.register_blueprint(xxx_bp, url_prefix='/api/{domain}/xxx')

    if __name__ == '__main__':
        with app.app_context():
            db.create_all()
        service.run()
"""
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import redis


class DomainServiceBase:
    """领域服务基座 — 所有配置从外部 config 对象读取，不硬编码。"""

    def __init__(self, config, db_instance=None):
        """
        Args:
            config: 领域服务的配置模块/类，至少需包含:
                - SERVICE_NAME: str  服务名称
                - PORT: int          监听端口
                - SQLALCHEMY_DATABASE_URI: str  数据库连接串
                - JWT_SECRET_KEY: str           JWT签名密钥(与核心服务共用)
                - JWT_ACCESS_TOKEN_EXPIRES: timedelta (可选)
                - REDIS_URL: str (可选，默认 redis://127.0.0.1:6379/0)
        """
        self.config = config
        self.service_name = config.SERVICE_NAME
        self.port = config.PORT

        self.app = Flask(self.service_name)
        self.app.config.from_object(config)

        # 数据库
        self.db = db_instance or SQLAlchemy()
        self.db.init_app(self.app)

        # JWT — 与核心服务共用同一 secret，验证同一 Token
        self.jwt = JWTManager(self.app)

        # CORS
        CORS(self.app)

        # Redis
        redis_url = getattr(config, 'REDIS_URL', 'redis://127.0.0.1:6379/0')
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

        self._register_error_handlers()
        self._register_health_check()

    # ------------------------------------------------------------------
    # 错误处理
    # ------------------------------------------------------------------
    def _register_error_handlers(self):
        @self.app.errorhandler(400)
        def bad_request(e):
            return jsonify({
                'code': 400,
                'error': 'Bad request',
                'service': self.service_name,
            }), 400

        @self.app.errorhandler(404)
        def not_found(e):
            return jsonify({
                'code': 404,
                'error': 'Not found',
                'service': self.service_name,
            }), 404

        @self.app.errorhandler(405)
        def method_not_allowed(e):
            return jsonify({
                'code': 405,
                'error': 'Method not allowed',
                'service': self.service_name,
            }), 405

        @self.app.errorhandler(500)
        def server_error(e):
            return jsonify({
                'code': 500,
                'error': 'Internal server error',
                'service': self.service_name,
            }), 500

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------
    def _register_health_check(self):
        @self.app.route('/health')
        def health():
            return jsonify({
                'service': self.service_name,
                'status': 'ok',
                'port': self.port,
            })

        # 也注册到 /api/{domain}/health 供网关代理访问
        @self.app.route('/api/<domain>/health')
        def health_with_prefix(domain):
            return jsonify({
                'service': self.service_name,
                'status': 'ok',
                'port': self.port,
                'domain': domain,
            })

    # ------------------------------------------------------------------
    # 启动
    # ------------------------------------------------------------------
    def run(self, debug=False):
        """启动领域服务。"""
        self.app.run(host='127.0.0.1', port=self.port, debug=debug)
