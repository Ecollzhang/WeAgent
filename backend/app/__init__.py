import os
import datetime
from flask import Flask, current_app, send_from_directory, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')


def _migrate_existing_tables():
    """Add new columns to existing tables without dropping data."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)

    # agents table
    if 'agents' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('agents')]
        with db.engine.connect() as conn:
            if 'avatar_color' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN avatar_color VARCHAR(20) DEFAULT ""'))
            if 'skill' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN skill TEXT'))
            if 'class_id' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN class_id VARCHAR(36) DEFAULT NULL'))
            if 'user_id' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN user_id VARCHAR(36) DEFAULT NULL'))
            if 'tool_ids' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN tool_ids JSON DEFAULT NULL'))
            if 'is_public' not in cols:
                conn.execute(text('ALTER TABLE agents ADD COLUMN is_public BOOLEAN DEFAULT TRUE'))
            conn.commit()

    # agent_categories table
    if 'agent_categories' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('agent_categories')]
        with db.engine.connect() as conn:
            if 'user_id' not in cols:
                conn.execute(text('ALTER TABLE agent_categories ADD COLUMN user_id VARCHAR(36) DEFAULT NULL'))
            conn.commit()

    # conversation_participants table
    if 'conversation_participants' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('conversation_participants')]
        with db.engine.connect() as conn:
            if 'participant_name' not in cols:
                conn.execute(text('ALTER TABLE conversation_participants ADD COLUMN participant_name VARCHAR(200) DEFAULT ""'))
            if 'participant_avatar' not in cols:
                conn.execute(text('ALTER TABLE conversation_participants ADD COLUMN participant_avatar VARCHAR(500) DEFAULT ""'))
            if 'participant_color' not in cols:
                conn.execute(text('ALTER TABLE conversation_participants ADD COLUMN participant_color VARCHAR(20) DEFAULT ""'))
            conn.commit()

    # messages table — add elements JSON column
    if 'messages' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('messages')]
        with db.engine.connect() as conn:
            if 'elements' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN elements JSON DEFAULT NULL'))
            if 'round_id' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN round_id VARCHAR(36) DEFAULT NULL'))
            if 'run_id' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN run_id VARCHAR(36) DEFAULT NULL'))
            if 'status' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT "done"'))
            if 'raw_output' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN raw_output TEXT DEFAULT NULL'))
            if 'meta' not in cols:
                conn.execute(text('ALTER TABLE messages ADD COLUMN meta JSON DEFAULT NULL'))
            conn.commit()

    # artifacts table — owner for message-less artifacts and ACL auditing
    if 'artifacts' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('artifacts')]
        with db.engine.connect() as conn:
            if 'owner_user_id' not in cols:
                conn.execute(text(
                    'ALTER TABLE artifacts ADD COLUMN owner_user_id VARCHAR(36) DEFAULT NULL'
                ))
            conn.commit()

    # conversations table — sandbox lifecycle columns
    if 'conversations' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('conversations')]
        with db.engine.connect() as conn:
            if 'is_favorite' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0'))
            if 'sandbox_session_id' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_session_id VARCHAR(100) DEFAULT NULL'))
            if 'sandbox_container_id' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_container_id VARCHAR(128) DEFAULT NULL'))
            if 'sandbox_host_port' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_host_port INTEGER DEFAULT NULL'))
            if 'sandbox_status' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_status VARCHAR(20) NOT NULL DEFAULT "pending"'))
            if 'last_active_at' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN last_active_at DATETIME DEFAULT NULL'))
            if 'stopped_at' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN stopped_at DATETIME DEFAULT NULL'))
            if 'sandbox_generation' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_generation INTEGER NOT NULL DEFAULT 1'))
            if 'sandbox_expires_at' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_expires_at DATETIME DEFAULT NULL'))
            if 'sandbox_snapshot_path' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_snapshot_path VARCHAR(500) DEFAULT NULL'))
            if 'sandbox_snapshot_sha256' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_snapshot_sha256 VARCHAR(64) DEFAULT NULL'))
            if 'sandbox_snapshot_size' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_snapshot_size INTEGER DEFAULT NULL'))
            if 'sandbox_snapshot_at' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_snapshot_at DATETIME DEFAULT NULL'))
            if 'workspace_id' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN workspace_id VARCHAR(36) DEFAULT NULL'))
            if 'kb_domain' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN kb_domain VARCHAR(20) NOT NULL DEFAULT ""'))
            if 'sandbox_server_fallback' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_server_fallback BOOLEAN NOT NULL DEFAULT 0'))
            if 'sandbox_agent_adapters' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_agent_adapters JSON DEFAULT NULL'))
            if 'sandbox_agent_service_views' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN sandbox_agent_service_views JSON DEFAULT NULL'))
            if 'kb_document_ids' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN kb_document_ids JSON DEFAULT NULL'))
            if 'services' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN services JSON DEFAULT NULL'))
            if 'project_id' not in cols:
                conn.execute(text('ALTER TABLE conversations ADD COLUMN project_id VARCHAR(36) DEFAULT NULL'))
            conn.commit()

    # workspaces table — sub_role column
    if 'workspaces' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('workspaces')]
        with db.engine.connect() as conn:
            if 'sub_role' not in cols:
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN sub_role VARCHAR(20) DEFAULT ''"))
            conn.commit()

    # users table — role column
    if 'users' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('users')]
        with db.engine.connect() as conn:
            if 'role' not in cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT "user"'))
            conn.commit()

    # user_model_configs table
    if 'user_model_configs' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('user_model_configs')]
        with db.engine.connect() as conn:
            if 'custom_model' not in cols:
                conn.execute(text('ALTER TABLE user_model_configs ADD COLUMN custom_model VARCHAR(100) NOT NULL DEFAULT ""'))
            conn.commit()

    # agents / capabilities / toolset_categories / agent_categories — domain isolation
    for table in ['agents', 'capabilities', 'toolset_categories', 'agent_categories']:
        if table in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns(table)]
            with db.engine.connect() as conn:
                if 'domain' not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN domain VARCHAR(50) DEFAULT 'rd' COMMENT 'rd / edu / office'"))
                conn.commit()

    # capabilities table
    if 'capabilities' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('capabilities')]
        with db.engine.connect() as conn:
            if 'category_id' not in cols:
                conn.execute(text('ALTER TABLE capabilities ADD COLUMN category_id VARCHAR(36) DEFAULT NULL'))
            conn.commit()

    # grayscale_config — add domains JSON column
    if 'grayscale_config' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('grayscale_config')]
        with db.engine.connect() as conn:
            if 'domains' not in cols:
                conn.execute(text('ALTER TABLE grayscale_config ADD COLUMN domains JSON DEFAULT NULL'))
            conn.commit()

    # workspaces / grayscale_config tables — create and seed
    if 'workspaces' not in inspector.get_table_names():
        with db.engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS workspaces ("
                "  id VARCHAR(36) NOT NULL PRIMARY KEY,"
                "  user_id VARCHAR(36) NOT NULL,"
                "  domain VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',"
                "  sub_role VARCHAR(20) DEFAULT '' COMMENT 'edu domain: teacher / student',"
                "  name VARCHAR(200) NOT NULL,"
                "  description TEXT DEFAULT NULL,"
                "  icon VARCHAR(50) DEFAULT 'default',"
                "  sort_order INT DEFAULT 0,"
                "  status ENUM('active','archived') DEFAULT 'active',"
                "  created_at DATETIME NOT NULL DEFAULT (now()),"
                "  updated_at DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,"
                "  INDEX idx_user (user_id),"
                "  INDEX idx_domain (domain),"
                "  UNIQUE KEY uk_user_domain_name (user_id, domain, name),"
                "  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                ")"
            ))
            conn.commit()
    if 'grayscale_config' not in inspector.get_table_names():
        with db.engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS grayscale_config ("
                "  id INT AUTO_INCREMENT PRIMARY KEY,"
                "  config_key VARCHAR(100) NOT NULL,"
                "  config_name VARCHAR(200) NOT NULL,"
                "  config_type ENUM('ui','feature','agent','tool') NOT NULL,"
                "  domain VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',"
                "  enabled TINYINT(1) NOT NULL DEFAULT 1,"
                "  visible TINYINT(1) NOT NULL DEFAULT 1,"
                "  description TEXT DEFAULT NULL,"
                "  metadata JSON DEFAULT NULL,"
                "  created_at DATETIME NOT NULL DEFAULT (now()),"
                "  updated_at DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,"
                "  UNIQUE KEY uk_key_domain (config_key, domain),"
                "  INDEX idx_domain (domain),"
                "  INDEX idx_type (config_type)"
                ")"
            ))
            conn.commit()
    _seed_grayscale_configs()
    _migrate_grayscale_configs()
    _seed_default_workspaces()


def _migrate_grayscale_configs():
    """Update existing grayscale configs without overriding operator choices."""
    from sqlalchemy import bindparam as _bindparam, text as _text, inspect as _inspect
    inspector = _inspect(db.engine)
    if 'grayscale_config' not in inspector.get_table_names():
        return

    import json as _json2
    all_domains_json = _json2.dumps(['rd', 'edu', 'office'])

    with db.engine.connect() as conn:
        # 1. Delete configs that are no longer used (not in wired list)
        wired_keys = {
            'ui.chat.workspace', 'ui.chat.services', 'ui.chat.attachments',
            'ui.sidebar.agents', 'ui.sidebar.tools', 'ui.sidebar.favorites',
            'ui.sidebar.knowledge',
            'ui.sidebar.projects', 'ui.sidebar.repos', 'ui.sidebar.reviews', 'ui.sidebar.builds',
            'ui.sidebar.courses', 'ui.sidebar.assignments', 'ui.sidebar.resources',
            'ui.sidebar.grades', 'ui.sidebar.students',
            'ui.sidebar.documents', 'ui.sidebar.meetings', 'ui.sidebar.approvals',
            'ui.sidebar.reports', 'ui.sidebar.schedules',
            'feature.education.enabled',
            'feature.education.chat.enabled',
            'feature.education.chat.manual_create',
            'feature.education.chat.tools',
            'feature.education.rag.enabled',
            'ui.chat.header.compact_title',
            # RD 领域卡片
            'ui.chat.card.requirement', 'ui.chat.card.bug', 'ui.chat.card.iteration', 'ui.chat.card.project',
            'ui.chat.card.education',
            # 聊天标签页
            'ui.chat.tabs.agent_config', 'ui.chat.tabs.artifacts', 'ui.chat.tabs.logs',
            'ui.chat.tabs.workflow', 'ui.chat.tabs.knowledge_base',
        }
        cleanup_statement = _text(
            "DELETE FROM grayscale_config WHERE config_key NOT IN :keys"
        ).bindparams(_bindparam("keys", expanding=True))
        conn.execute(cleanup_statement, {'keys': sorted(wired_keys)})

        # 2. Move shared sidebar entries from rd/edu/office to common domain
        shared_keys = ['ui.sidebar.agents', 'ui.sidebar.tools', 'ui.sidebar.favorites', 'ui.sidebar.knowledge']
        for key in shared_keys:
            # Check if common entry already exists
            exists = conn.execute(_text(
                "SELECT id FROM grayscale_config WHERE config_key = :key AND domain = 'common'"
            ), {'key': key}).first()
            if not exists:
                # Insert into common with all domains
                # Get name/type from any existing per-domain entry
                existing = conn.execute(_text(
                    "SELECT config_name, config_type FROM grayscale_config WHERE config_key = :key LIMIT 1"
                ), {'key': key}).first()
                if existing:
                    conn.execute(_text(
                        "INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible, domains) "
                        "VALUES (:key, :name, :type, 'common', 1, 1, :domains)"
                    ), {'key': key, 'name': existing[0], 'type': existing[1], 'domains': all_domains_json})
            else:
                # Update domains if null
                conn.execute(_text(
                    "UPDATE grayscale_config SET domains = :domains WHERE config_key = :key AND domain = 'common' AND domains IS NULL"
                ), {'key': key, 'domains': all_domains_json})
            # Delete per-domain entries for these shared keys
            conn.execute(_text(
                "DELETE FROM grayscale_config WHERE config_key = :key AND domain != 'common'"
            ), {'key': key})

        # 3. Ensure chat feature configs exist in common with domains
        chat_keys = ['ui.chat.workspace', 'ui.chat.services', 'ui.chat.attachments']
        for key in chat_keys:
            exists = conn.execute(_text(
                "SELECT id FROM grayscale_config WHERE config_key = :key AND domain = 'common'"
            ), {'key': key}).first()
            if not exists:
                # Get name/type from any existing entry
                existing = conn.execute(_text(
                    "SELECT config_name, config_type FROM grayscale_config WHERE config_key = :key LIMIT 1"
                ), {'key': key}).first()
                name = existing[0] if existing else key
                ctype = existing[1] if existing else 'ui'
                conn.execute(_text(
                    "INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible, domains) "
                    "VALUES (:key, :name, :type, 'common', 1, 1, :domains)"
                ), {'key': key, 'name': name, 'type': ctype, 'domains': all_domains_json})
            else:
                conn.execute(_text(
                    "UPDATE grayscale_config SET domains = :domains WHERE config_key = :key AND domain = 'common' AND domains IS NULL"
                ), {'key': key, 'domains': all_domains_json})
            # Remove any per-domain duplicates of chat configs
            conn.execute(_text(
                "DELETE FROM grayscale_config WHERE config_key = :key AND domain != 'common'"
            ), {'key': key})

        # 5. Ensure domain card configs exist in common
        card_keys = [
            ('ui.chat.card.requirement', '聊天-需求卡片'),
            ('ui.chat.card.bug', '聊天-缺陷卡片'),
            ('ui.chat.card.iteration', '聊天-迭代卡片'),
            ('ui.chat.card.project', '聊天-项目卡片'),
        ]
        rd_domains_json = _json2.dumps(['rd'])
        for key, name in card_keys:
            exists = conn.execute(_text(
                "SELECT id FROM grayscale_config WHERE config_key = :key AND domain = 'common'"
            ), {'key': key}).first()
            if not exists:
                conn.execute(_text(
                    "INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible, domains) "
                    "VALUES (:key, :name, 'ui', 'common', 1, 1, :domains)"
                ), {'key': key, 'name': name, 'domains': rd_domains_json})
            conn.execute(_text(
                "UPDATE grayscale_config SET domains = :domains "
                "WHERE config_key = :key AND domain = 'common'"
            ), {'key': key, 'domains': rd_domains_json})
            # Remove any per-domain duplicates
            conn.execute(_text(
                "DELETE FROM grayscale_config WHERE config_key = :key AND domain != 'common'"
            ), {'key': key})

        education_chat_flags = [
            ('feature.education.chat.enabled', 'Education chat', 'feature'),
            ('feature.education.chat.manual_create', 'Education manual conversation', 'feature'),
            ('feature.education.chat.tools', 'Education chat tools', 'feature'),
            ('feature.education.rag.enabled', 'Education course knowledge search', 'feature'),
            ('ui.chat.header.compact_title', 'Education compact chat title', 'ui'),
        ]
        for key, name, config_type in education_chat_flags:
            exists = conn.execute(_text(
                "SELECT id FROM grayscale_config "
                "WHERE config_key = :key AND domain = 'edu'"
            ), {'key': key}).first()
            if not exists:
                conn.execute(_text(
                    "INSERT INTO grayscale_config "
                    "(config_key, config_name, config_type, domain, enabled, visible, domains) "
                    "VALUES (:key, :name, :config_type, 'edu', 1, 1, NULL)"
                ), {'key': key, 'name': name, 'config_type': config_type})
            conn.execute(_text(
                "DELETE FROM grayscale_config "
                "WHERE config_key = :key AND domain != 'edu'"
            ), {'key': key})

        education_card_key = 'ui.chat.card.education'
        education_domains_json = _json2.dumps(['edu'])
        exists = conn.execute(_text(
            "SELECT id FROM grayscale_config "
            "WHERE config_key = :key AND domain = 'common'"
        ), {'key': education_card_key}).first()
        if not exists:
            conn.execute(_text(
                "INSERT INTO grayscale_config "
                "(config_key, config_name, config_type, domain, enabled, visible, domains) "
                "VALUES (:key, :name, 'ui', 'common', 1, 1, :domains)"
            ), {
                'key': education_card_key,
                'name': 'Chat - Education card',
                'domains': education_domains_json,
            })
        conn.execute(_text(
            "UPDATE grayscale_config SET domains = :domains "
            "WHERE config_key = :key AND domain = 'common'"
        ), {'key': education_card_key, 'domains': education_domains_json})
        conn.execute(_text(
            "DELETE FROM grayscale_config "
            "WHERE config_key = :key AND domain != 'common'"
        ), {'key': education_card_key})

        # 6. Ensure chat tab configs exist in common
        chat_tab_keys = [
            ('ui.chat.tabs.agent_config', '聊天标签-Agent配置'),
            ('ui.chat.tabs.artifacts', '聊天标签-产物'),
            ('ui.chat.tabs.logs', '聊天标签-日志'),
            ('ui.chat.tabs.workflow', '聊天标签-工作流'),
            ('ui.chat.tabs.knowledge_base', '聊天标签-知识库'),
        ]
        for key, name in chat_tab_keys:
            exists = conn.execute(_text(
                "SELECT id FROM grayscale_config WHERE config_key = :key AND domain = 'common'"
            ), {'key': key}).first()
            if not exists:
                conn.execute(_text(
                    "INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible, domains) "
                    "VALUES (:key, :name, 'ui', 'common', 1, 1, :domains)"
                ), {'key': key, 'name': name, 'domains': all_domains_json})

        conn.commit()


def _seed_grayscale_configs():
    """Seed grayscale_config table if empty."""
    from sqlalchemy import text as _text, inspect as _inspect
    inspector = _inspect(db.engine)

    if 'grayscale_config' not in inspector.get_table_names():
        return

    with db.engine.connect() as conn:
        count = conn.execute(_text("SELECT COUNT(*) FROM grayscale_config")).scalar()
        if count > 0:
            return  # already seeded

        configs = [
            # ===== 公共 (common) — 对所有领域生效，通过 domains 字段指定 =====
            ('ui.chat.workspace', '聊天-工作目录', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.services', '聊天-预览服务', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.attachments', '聊天-上传文件', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.tabs.agent_config', '聊天标签-Agent配置', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.tabs.artifacts', '聊天标签-产物', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.tabs.logs', '聊天标签-日志', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.tabs.workflow', '聊天标签-工作流', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.tabs.knowledge_base', '聊天标签-知识库', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.sidebar.agents', '侧边栏-我的Agent', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.sidebar.tools', '侧边栏-工具集', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.sidebar.favorites', '侧边栏-我的收藏', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.sidebar.knowledge', '侧边栏-知识库', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.card.requirement', '聊天-需求卡片', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.card.bug', '聊天-缺陷卡片', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.card.iteration', '聊天-迭代卡片', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            ('ui.chat.card.project', '聊天-项目卡片', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
            # ===== 智能研发 (rd) =====
            ('ui.sidebar.projects', '侧边栏-项目管理', 'ui', 'rd', 1, 1),
            ('ui.sidebar.repos', '侧边栏-代码仓库', 'ui', 'rd', 1, 1),
            ('ui.sidebar.reviews', '侧边栏-代码审查', 'ui', 'rd', 1, 1),
            ('ui.sidebar.builds', '侧边栏-构建管理', 'ui', 'rd', 1, 1),
            # ===== 智慧教育 (edu) =====
            ('ui.sidebar.courses', '侧边栏-课程管理', 'ui', 'edu', 1, 1),
            ('ui.sidebar.assignments', '侧边栏-作业系统', 'ui', 'edu', 1, 1),
            ('ui.sidebar.resources', '侧边栏-教学资源', 'ui', 'edu', 1, 1),
            ('ui.sidebar.grades', '侧边栏-成绩管理', 'ui', 'edu', 1, 1),
            ('ui.sidebar.students', '侧边栏-学生画像', 'ui', 'edu', 1, 1),
            ('feature.education.enabled', 'Education feature', 'feature', 'edu', 1, 1),
            ('ui.chat.header.compact_title', 'Education compact chat title', 'ui', 'edu', 1, 1),
            # ===== 智慧办公 (office) =====
            ('ui.sidebar.documents', '侧边栏-公文管理', 'ui', 'office', 1, 1),
            ('ui.sidebar.meetings', '侧边栏-会议管理', 'ui', 'office', 1, 1),
            ('ui.sidebar.approvals', '侧边栏-审批流程', 'ui', 'office', 1, 1),
            ('ui.sidebar.reports', '侧边栏-报表服务', 'ui', 'office', 1, 1),
            ('ui.sidebar.schedules', '侧边栏-日程管理', 'ui', 'office', 1, 1),
        ]

        for item in configs:
            key, name, ctype, domain, enabled, visible = item[:6]
            domains = item[6] if len(item) > 6 else None
            import json as _json
            conn.execute(_text(
                "INSERT INTO grayscale_config "
                "(config_key, config_name, config_type, domain, enabled, visible, domains) "
                "VALUES (:key, :name, :type, :domain, :enabled, :visible, :domains)"
            ), {
                'key': key, 'name': name, 'type': ctype,
                'domain': domain, 'enabled': enabled, 'visible': visible,
                'domains': _json.dumps(domains) if domains else None,
            })
        conn.commit()


def _seed_default_workspaces():
    """为已有用户在各领域创建默认工作空间，并将已有会话关联到研发空间。"""
    import uuid as _uuid
    from datetime import datetime as _dt

    # 仅在表存在时执行
    from sqlalchemy import inspect as _inspect, text as _text
    inspector = _inspect(db.engine)
    if 'workspaces' not in inspector.get_table_names():
        return
    if 'conversations' not in inspector.get_table_names():
        return
    if 'users' not in inspector.get_table_names():
        return

    # 获取所有用户
    with db.engine.connect() as conn:
        result = conn.execute(_text("SELECT id FROM users"))
        all_user_ids = [row[0] for row in result]

    now = _dt.utcnow()

    for user_id in all_user_ids:
        # 检查用户在哪些领域还没有工作空间
        with db.engine.connect() as conn:
            existing = conn.execute(
                _text("SELECT domain FROM workspaces WHERE user_id = :uid"),
                {'uid': user_id}
            )
            existing_domains = {row[0] for row in existing}

        # 为缺失的领域创建默认空间
        domain_defaults = [
            ('rd', '我的研发空间', '系统自动创建的默认研发工作空间'),
            ('edu', '我的教育空间', '系统自动创建的默认智慧教育工作空间'),
            ('office', '我的办公空间', '系统自动创建的默认智慧办公工作空间'),
        ]
        for domain, name, desc in domain_defaults:
            if domain in existing_domains:
                continue
            ws_id = str(_uuid.uuid4())
            with db.engine.connect() as conn:
                conn.execute(_text(
                    "INSERT INTO workspaces (id, user_id, domain, name, description, icon, "
                    "status, created_at, updated_at) "
                    "VALUES (:id, :uid, :domain, :name, :desc, 'default', 'active', :now, :now)"
                ), {'id': ws_id, 'uid': user_id, 'domain': domain, 'name': name, 'desc': desc, 'now': now})
                conn.commit()

    # 将旧会话按其可信领域回填到对应工作空间（逐条处理，兼容 SQLite）。
    with db.engine.connect() as conn:
        result = conn.execute(
            _text(
                "SELECT c.id, c.owner_id, c.kb_domain "
                "FROM conversations c WHERE c.workspace_id IS NULL"
            )
        )
        orphan_convs = [(row[0], row[1], row[2]) for row in result]

    for conv_id, owner_id, kb_domain in orphan_convs:
        target_domain = kb_domain if kb_domain in {'rd', 'edu', 'office'} else 'rd'
        with db.engine.connect() as conn:
            ws = conn.execute(
                _text(
                    "SELECT w.id FROM workspaces w "
                    "WHERE w.user_id = :uid AND w.domain = :domain "
                    "AND w.status = 'active' LIMIT 1"
                ),
                {'uid': owner_id, 'domain': target_domain}
            ).fetchone()
            if ws:
                conn.execute(
                    _text("UPDATE conversations SET workspace_id = :ws_id WHERE id = :cid"),
                    {'ws_id': ws[0], 'cid': conv_id}
                )
                conn.commit()


def create_app(config_name=None):
    """Flask application factory."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load the core configuration by file path. Domain services also have
    # top-level ``config.py`` modules and may be imported in the same process.
    import importlib.util
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
    config_spec = importlib.util.spec_from_file_location(
        'weagent_core_config', os.path.abspath(config_path)
    )
    config_module = importlib.util.module_from_spec(config_spec)
    config_spec.loader.exec_module(config_module)
    config_by_name = config_module.config_by_name
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
        async_mode='threading',
    )

    # Register blueprints
    from app.controllers.auth_controller import auth_bp
    from app.controllers.conversation_controller import conversation_bp
    from app.controllers.message_controller import message_bp
    from app.controllers.agent_controller import agent_bp
    from app.controllers.artifact_controller import artifact_bp
    from app.controllers.tool_controller import tool_bp
    from app.controllers.toolset_controller import toolset_bp
    from app.controllers.upload_controller import upload_bp
    from app.controllers.settings_controller import settings_bp
    from app.controllers.capability_controller import capability_bp, agent_capability_bp
    from app.controllers.workspace_controller import workspace_bp
    from app.controllers.grayscale_controller import grayscale_bp
    from app.controllers.domain_proxy_controller import domain_proxy_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(conversation_bp, url_prefix='/api/conversations')
    app.register_blueprint(message_bp, url_prefix='/api/messages')
    app.register_blueprint(agent_bp, url_prefix='/api/agents')
    app.register_blueprint(artifact_bp, url_prefix='/api/artifacts')
    app.register_blueprint(tool_bp, url_prefix='/api/tools')
    app.register_blueprint(toolset_bp, url_prefix='/api/toolsets')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(capability_bp, url_prefix='/api/capabilities')
    app.register_blueprint(agent_capability_bp, url_prefix='/api/agents')
    app.register_blueprint(workspace_bp)
    app.register_blueprint(grayscale_bp)
    app.register_blueprint(domain_proxy_bp)

    # Register sandbox blueprint (optional, for testing)
    try:
        from app.sandbox.api.routes import sandbox_bp
        app.register_blueprint(sandbox_bp, url_prefix='/api/sandbox')
    except ImportError as e:
        print(f'[WeAgent] Sandbox blueprint not loaded: {e}')

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), '..', 'uploads'))
        return send_from_directory(os.path.abspath(upload_dir), filename)

    # Initialize Redis client
    from app.utils.redis_client import redis_client
    redis_client.init_app(app)

    # Register SocketIO event handlers. The decorators in app.socket.events
    # only take effect after the module is imported.
    try:
        import importlib
        importlib.import_module('app.socket.events')
    except Exception as e:
        print(f'[WeAgent] Socket events not loaded: {e}')

    # Auto-create tables and seed data (development convenience)
    with app.app_context():
        # Import all models so SQLAlchemy knows about them
        from app.models.user import User
        from app.models.conversation import Conversation, ConversationParticipant
        from app.models.message import Message
        from app.models.agent import Agent
        from app.models.agent_category import AgentCategory
        from app.models.artifact import Artifact
        from app.models.agent_tool import AgentTool
        from app.models.toolset_category import ToolsetCategory
        from app.models.user_model_config import UserModelConfig
        from app.models.agent_run import AgentRun
        from app.models.capability import (
            AgentCapabilityBinding,
            Capability,
            CapabilityCallRecord,
            CapabilityImportJob,
            CapabilitySecurityAudit,
            CapabilityVersion,
            CapabilityVersionAsset,
            SkillRevisionDraft,
        )

        db.create_all()

        # Migrate existing tables — add new columns if missing
        _migrate_existing_tables()

        # Seed default data
        try:
            from app.services.agent_service import agent_service
            agent_service.seed_default_data()
        except Exception as e:
            print(f'[WeAgent] Seed note: {e}')

        # Seed default tools
        try:
            from app.services.tool_service import tool_service
            tool_service.seed_default_tools()
        except Exception as e:
            print(f'[WeAgent] Tool seed note: {e}')

        # Seed default toolset categories
        try:
            from app.services.toolset_category_service import toolset_category_service
            toolset_category_service.seed_builtin_categories()
        except Exception as e:
            print(f'[WeAgent] Toolset category seed note: {e}')

        # Seed capability wrappers for built-in platform tools
        try:
            from app.services.capability_service import capability_service
            capability_service.seed_builtin_tool_capabilities()
            capability_service.seed_education_agent_tool_bindings()
        except Exception as e:
            print(f'[WeAgent] Capability seed note: {e}')

    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        from app.utils.response import error_response
        return error_response('Resource not found', code=404)

    @app.errorhandler(500)
    def internal_error(error):
        from app.utils.response import error_response
        return error_response('Internal server error', code=500)

    # Request logging
    @app.after_request
    def log_request(response):
        now = datetime.datetime.now().strftime('%H:%M:%S')
        print(f'[WeAgent] {now} {request.method} {request.path} -> {response.status_code}')
        return response

    # Health check
    @app.route('/api/health')
    def health_check():
        from app.utils.response import success_response
        return success_response({'status': 'healthy'})

    return app
