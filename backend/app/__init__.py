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
            conn.commit()


def create_app(config_name=None):
    """Flask application factory."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load configuration
    from config import config_by_name
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
    from app.controllers.upload_controller import upload_bp
    from app.controllers.settings_controller import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(conversation_bp, url_prefix='/api/conversations')
    app.register_blueprint(message_bp, url_prefix='/api/messages')
    app.register_blueprint(agent_bp, url_prefix='/api/agents')
    app.register_blueprint(artifact_bp, url_prefix='/api/artifacts')
    app.register_blueprint(tool_bp, url_prefix='/api/tools')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

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
        from app.models.user_model_config import UserModelConfig
        from app.models.agent_run import AgentRun

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
