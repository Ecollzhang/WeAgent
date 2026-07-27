"""WeAgent Education domain service."""

import os
import sys

from flask import jsonify, request


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.domain_base import DomainServiceBase

try:
    from .config import Config
    from .extensions import db
except ImportError:  # Support ``python services/edu/app.py``.
    from config import Config
    from extensions import db


def create_edu_app(config_object=Config):
    """Create an isolated Education application for production or tests."""
    service = DomainServiceBase(config_object, db_instance=db)
    app = service.app
    app.extensions["domain_service"] = service

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
    except ImportError:
        from routes import education_api
        from workflow_routes import education_workflow_api
    app.register_blueprint(education_api, url_prefix="/api/edu")
    app.register_blueprint(education_workflow_api, url_prefix="/api/edu")
    return app


app = create_edu_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    service = app.extensions["domain_service"]
    print(f"[WeAgent] Education service listening on http://127.0.0.1:{service.port}")
    service.run(debug=True)
