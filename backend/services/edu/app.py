"""WeAgent 智慧教育领域服务.

启动方式:
    cd services/edu
    python app.py
"""
import sys
import os

from config import Config

# 确保能导入共享核心 app 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.domain_base import DomainServiceBase

service = DomainServiceBase(Config)
app = service.app
db = service.db

# ── TODO: 在此注册领域专属蓝图 ──────────────────────────────
# 示例:
#   from controllers.xxx_controller import xxx_bp
#   app.register_blueprint(xxx_bp, url_prefix='/api/edu/xxx')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(f'[WeAgent] 智慧教育服务启动 → http://127.0.0.1:{Config.PORT}')
    service.run(debug=True)
