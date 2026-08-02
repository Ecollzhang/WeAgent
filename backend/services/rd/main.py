"""WeAgent 智能研发领域服务.

启动方式:
    cd services/rd
    python main.py
"""
import sys
import os

# 先导入本地 config（必须在 sys.path 修改之前，避免被 backend/config.py 覆盖）
from config import Config

# 将 backend/ 加入 sys.path 末尾，以便导入核心包 app（weagent_core）
# 注意：必须用 append（不是 insert(0)），否则 backend/config.py 和 backend/app/
# 会覆盖本地的 config.py 和 main.py 的模块解析
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(_backend_dir)

from app.services.domain_base import DomainServiceBase  # noqa: E402

from flask import jsonify  # noqa: E402
from flask_jwt_extended import jwt_required  # noqa: E402
from database import init_db  # noqa: E402
from app.sandbox.service_spec import ServiceSpec, ServiceEndpoint, ServiceCapability  # noqa: E402

service = DomainServiceBase(Config)
app = service.app
db = service.db
init_db(db)

# ── 服务自描述 (Service Spec) ──────────────────────────────
@app.route('/api/rd/spec')
def api_spec():
    """返回 RD 服务的接口描述，Agent 可通过此端点自动发现所有可用接口。"""
    spec = ServiceSpec(
        service="rd",
        version="1.0.0",
        description="智能研发领域服务 — 项目管理、需求、缺陷、迭代、代码审查、构建、代码仓库",
        base_url=f"http://localhost:{Config.PORT}",
        status="healthy",
        capabilities=[
            ServiceCapability("项目管理", "创建和管理研发项目"),
            ServiceCapability("需求管理", "需求的CRUD、状态流转、分配、子需求"),
            ServiceCapability("缺陷跟踪", "Bug的CRUD、状态流转、分配、关联需求"),
            ServiceCapability("迭代管理", "迭代规划与进度跟踪"),
            ServiceCapability("代码仓库", "GitHub仓库连接、文件树浏览、分支管理"),
            ServiceCapability("代码审查", "AI辅助代码审查（script/diff模式）"),
            ServiceCapability("构建管理", "触发和监控CI/CD构建（GitHub Actions集成）"),
            ServiceCapability("成员协作", "项目成员管理与角色分配"),
            ServiceCapability("甘特图", "迭代和需求的甘特图数据"),
        ],
        popular_endpoints=[
            ServiceEndpoint("GET",  "/api/rd/projects",                       "获取项目列表", params={"workspace_id": "可选，工作空间ID"}),
            ServiceEndpoint("POST", "/api/rd/projects",                       "创建新项目", body={"name": "项目名称", "description": "描述", "tech_stack": {"frontend":"","backend":""}}),
            ServiceEndpoint("GET",  "/api/rd/projects/{id}",                  "获取项目详情"),
            ServiceEndpoint("GET",  "/api/rd/projects/{id}/requirements",     "获取需求列表", params={"status":"", "priority":"", "iteration_id":"", "assignee_id":""}),
            ServiceEndpoint("POST", "/api/rd/projects/{id}/requirements",     "创建需求", body={"title":"标题","description":"描述","priority":"p0/p1/p2/p3","iteration_id":"可选"}),
            ServiceEndpoint("GET",  "/api/rd/projects/{id}/bugs",             "获取缺陷列表", params={"status":"","severity":"","iteration_id":""}),
            ServiceEndpoint("POST", "/api/rd/projects/{id}/bugs",             "创建缺陷", body={"title":"标题","description":"复现步骤","severity":"blocker/critical/major/minor/trivial"}),
            ServiceEndpoint("GET",  "/api/rd/projects/{id}/iterations",       "获取迭代列表"),
            ServiceEndpoint("POST", "/api/rd/projects/{id}/iterations",       "创建迭代", body={"name":"名称","goal":"目标","start_date":"","end_date":""}),
            ServiceEndpoint("GET",  "/api/rd/projects/{id}/builds",           "获取构建列表", params={"status":"","branch":""}),
            ServiceEndpoint("POST", "/api/rd/projects/{id}/builds",           "触发构建", body={"repo_id":"仓库ID","workflow_id":"","branch":"main"}),
            ServiceEndpoint("POST", "/api/rd/projects/{id}/reviews",          "提交代码审查", body={"title":"标题","code_content":"代码","language":"语言"}),
        ],
        all_endpoints=[],  # 完整列表过长，Agent 按需通过 /spec 查看
    )
    return jsonify(spec.to_dict())


@app.route('/api/rd/health')
def rd_health():
    """健康检查端点。"""
    try:
        from sqlalchemy import text as sa_text
        db.session.execute(sa_text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "1.0.0",
        "uptime_seconds": 0,  # RD 服务不追踪启动时间，设为 0
        "dependencies": {
            "database": db_status,
        },
    })

# ── 注册领域专属蓝图 ──────────────────────────────
from controllers.project_controller import project_bp  # noqa: E402
from controllers.iteration_controller import iteration_bp  # noqa: E402
from controllers.requirement_controller import requirement_bp  # noqa: E402
from controllers.bug_controller import bug_bp  # noqa: E402
from controllers.comment_controller import comment_bp  # noqa: E402
from controllers.branch_controller import branch_bp  # noqa: E402
from controllers.member_controller import member_bp  # noqa: E402
from controllers.activity_controller import activity_bp  # noqa: E402
from controllers.repo_controller import repo_bp  # noqa: E402
from controllers.review_controller import review_bp  # noqa: E402
from controllers.build_controller import build_bp  # noqa: E402

app.register_blueprint(project_bp)
app.register_blueprint(iteration_bp)
app.register_blueprint(requirement_bp)
app.register_blueprint(bug_bp)
app.register_blueprint(comment_bp)
app.register_blueprint(branch_bp)
app.register_blueprint(member_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(repo_bp)
app.register_blueprint(review_bp)
app.register_blueprint(build_bp)



def _sync_model_configs(db, inspector):
    """Startup sync: copy model configs from main weagent DB to local rd_model_configs."""
    from sqlalchemy import text as sa_text
    import json

    # Ensure table exists (db.create_all() should handle this)
    if not inspector.has_table('rd_model_configs'):
        print('[Migration] Creating rd_model_configs table...')
        db.session.execute(sa_text(
            """CREATE TABLE rd_model_configs (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL UNIQUE,
                api_key TEXT NULL,
                base_url VARCHAR(500) NULL,
                model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o',
                custom_model VARCHAR(100) NOT NULL DEFAULT '',
                temperature FLOAT NOT NULL DEFAULT 0.7,
                max_tokens INT NOT NULL DEFAULT 4096,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        ))
        db.session.flush()

    # Try to sync from main weagent DB
    try:
        from config import Config
        main_db_url = Config.SQLALCHEMY_DATABASE_URI.replace(
            '/weagent_rd?', '/weagent?'
        ).replace('/weagent_rd', '/weagent')
        # Only sync if there are no configs yet in local DB
        from models.rd_model_config import RdModelConfig
        existing = RdModelConfig.query.count()
        if existing > 0:
            print(f'[ModelConfig] Local table has {existing} config(s), skip sync')
            return

        from sqlalchemy import create_engine
        main_engine = create_engine(main_db_url)
        with main_engine.connect() as conn:
            rows = conn.execute(sa_text(
                'SELECT user_id, api_key, base_url, model, custom_model, temperature, max_tokens '
                'FROM user_model_configs'
            )).fetchall()
            if rows:
                import uuid
                for row in rows:
                    db.session.execute(sa_text(
                        """INSERT INTO rd_model_configs
                           (id, user_id, api_key, base_url, model, custom_model, temperature, max_tokens)
                           VALUES (:id, :uid, :key, :url, :model, :cm, :temp, :mt)
                           ON DUPLICATE KEY UPDATE
                           api_key=VALUES(api_key), base_url=VALUES(base_url),
                           model=VALUES(model), custom_model=VALUES(custom_model),
                           temperature=VALUES(temperature), max_tokens=VALUES(max_tokens)"""
                    ), {
                        'id': str(uuid.uuid4()),
                        'uid': row[0],
                        'key': row[1],
                        'url': row[2] or '',
                        'model': row[3] or 'gpt-4o',
                        'cm': row[4] or '',
                        'temp': row[5] or 0.7,
                        'mt': row[6] or 4096,
                    })
                db.session.flush()
                print(f'[ModelConfig] Synced {len(rows)} config(s) from main DB')
        main_engine.dispose()
    except Exception as e:
        print(f'[ModelConfig] Sync skipped (main DB not available or error): {e}')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 自动迁移：为已有表添加缺失的列 + 创建新表
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        migrate_cols = {
            'rd_requirements': ['developer_id', 'designer_id', 'tester_id'],
            'rd_bugs': ['developer_id', 'designer_id', 'tester_id'],
        }
        for table, cols in migrate_cols.items():
            if inspector.has_table(table):
                existing = {c['name'] for c in inspector.get_columns(table)}
                for col in cols:
                    if col not in existing:
                        db.session.execute(text(
                            f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR(36) NULL"
                        ))
                        print(f'[Migration] Added {col} to {table}')
        # 确保 rd_activity_logs 的 target_type ENUM 包含 'review' 和 'branch'
        if inspector.has_table('rd_activity_logs'):
            db.session.execute(text(
                """ALTER TABLE rd_activity_logs MODIFY COLUMN target_type
                   ENUM('requirement','bug','iteration','project','review','branch')
                   NOT NULL"""
            ))
            print('[Migration] Updated rd_activity_logs.target_type ENUM')
        # 确保多对多关联表存在
        if not inspector.has_table('rd_bug_requirements'):
            db.session.execute(text(
                """CREATE TABLE rd_bug_requirements (
                    bug_id VARCHAR(36) NOT NULL,
                    requirement_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (bug_id, requirement_id),
                    FOREIGN KEY (bug_id) REFERENCES rd_bugs(id) ON DELETE CASCADE,
                    FOREIGN KEY (requirement_id) REFERENCES rd_requirements(id) ON DELETE CASCADE
                )"""
            ))
            print('[Migration] Created rd_bug_requirements table')
        # rd_reviews 加 review_method 列
        if inspector.has_table('rd_reviews'):
            review_cols = {c['name'] for c in inspector.get_columns('rd_reviews')}
            if 'review_method' not in review_cols:
                db.session.execute(text(
                    "ALTER TABLE rd_reviews ADD COLUMN review_method VARCHAR(20) NOT NULL DEFAULT 'script'"
                ))
                print('[Migration] Added review_method to rd_reviews')
        # rd_builds 加 repo_id, workflow_id, github_run_id 列
        if inspector.has_table('rd_builds'):
            build_cols = {c['name'] for c in inspector.get_columns('rd_builds')}
            build_migrations = {
                'repo_id': 'VARCHAR(36) NULL',
                'workflow_id': 'VARCHAR(100) NULL',
                'github_run_id': 'BIGINT NULL',
            }
            for col, col_def in build_migrations.items():
                if col not in build_cols:
                    db.session.execute(text(
                        f"ALTER TABLE rd_builds ADD COLUMN {col} {col_def}"
                    ))
                    print(f'[Migration] Added {col} to rd_builds')
        # 同步模型配置表
        _sync_model_configs(db, inspector)
        db.session.commit()
    print(f'[WeAgent] 智能研发服务启动 → http://127.0.0.1:{Config.PORT}')
    service.run(debug=True)
