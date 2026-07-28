"""WeAgent Education domain service."""

import os
import sys

from flask import jsonify, request


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.domain_base import DomainServiceBase
from services.edu.runtime_client import CoreRuntimeClient

try:
    from .config import Config
    from .extensions import db
except ImportError:  # Support ``python services/edu/app.py``.
    from services.edu.config import Config
    from services.edu.extensions import db


def create_edu_app(config_object=Config):
    """Create an isolated Education application for production or tests."""
    service = DomainServiceBase(config_object, db_instance=db)
    app = service.app
    app.extensions["domain_service"] = service
    app.extensions["education_runtime_client"] = CoreRuntimeClient()

    @app.before_request
    def enforce_feature_gate():
        if (
            request.path.startswith("/api/edu/")
            and request.path != "/api/edu/health"
            and not app.config.get("EDUCATION_FEATURE_ENABLED", True)
        ):
            return jsonify({"error": "Education feature is disabled"}), 404

    try:
        from .routes import education_api
        from .workflow_routes import education_workflow_api
        from .content_routes import education_content_api
        from .asset_routes import education_asset_api
        from .knowledge_routes import education_knowledge_api
        from .learning_routes import education_learning_api
        from .tool_routes import education_tool_api
    except ImportError:
        from services.edu.routes import education_api
        from services.edu.workflow_routes import education_workflow_api
        from services.edu.content_routes import education_content_api
        from services.edu.asset_routes import education_asset_api
        from services.edu.knowledge_routes import education_knowledge_api
        from services.edu.learning_routes import education_learning_api
        from services.edu.tool_routes import education_tool_api
    app.register_blueprint(education_api, url_prefix="/api/edu")
    app.register_blueprint(education_workflow_api, url_prefix="/api/edu")
    app.register_blueprint(education_content_api, url_prefix="/api/edu")
    app.register_blueprint(education_asset_api, url_prefix="/api/edu")
    app.register_blueprint(education_knowledge_api, url_prefix="/api/edu")
    app.register_blueprint(education_learning_api, url_prefix="/api/edu")
    app.register_blueprint(education_tool_api, url_prefix="/api/edu")

    @app.cli.command("migrate-education")
    def migrate_education_command():
        from .schema_maintenance import migrate_existing_education_schema

        db.create_all()
        changes = migrate_existing_education_schema()
        print(
            "Education schema is current"
            if not changes
            else f"Applied Education schema changes: {', '.join(changes)}"
        )
    return app


app = create_edu_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        try:
            from .schema_maintenance import migrate_existing_education_schema
        except ImportError:
            from services.edu.schema_maintenance import migrate_existing_education_schema
        migrate_existing_education_schema()
    service = app.extensions["domain_service"]
    print(f"[WeAgent] Education service listening on http://127.0.0.1:{service.port}")
    service.run(debug=True)
