"""
ReviewIn Backend — Application factory & entry point.

Flask application serving the REST API for the ReviewIn
peer-review classroom platform.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from config import config
from extensions import db, migrate, jwt, bcrypt, limiter


def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Initialize extensions ──
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    # ── CORS ──
    # Allow all explicit origins from FRONTEND_URL plus any localhost port
    import re
    _cors_origins = [o.strip() for o in app.config["FRONTEND_URL"].split(",") if o.strip()]
    _cors_origins.append(re.compile(r"http://localhost:\d+"))
    CORS(
        app,
        supports_credentials=True,
        origins=_cors_origins,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # ── Register blueprints ──
    _register_blueprints(app)

    # ── JWT token revocation check ──
    from routes.auth import is_token_revoked

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_revoked(jwt_header, jwt_payload)

    # ── Error handlers ──
    _register_error_handlers(app)

    # ── Health check ──
    @app.route("/health", methods=["GET"])
    def health_check():
        db_healthy = False
        try:
            db.session.execute(db.text("SELECT 1"))
            db.session.commit()
            db_healthy = True
        except Exception as e:
            app.logger.error(f"Database health check failed: {e}")
            db.session.rollback()

        return (
            jsonify(
                {
                    "status": "healthy" if db_healthy else "degraded",
                    "message": "ReviewIn API is running",
                    "database": "connected" if db_healthy else "error",
                }
            ),
            200 if db_healthy else 503,
        )

    # ── Session cleanup ──
    @app.after_request
    def after_request(response):
        try:
            db.session.remove()
        except Exception:
            pass
        return response

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    return app


def _register_blueprints(app):
    """Register all route blueprints."""
    from routes.auth import auth_bp
    from routes.classes import classes_bp
    from routes.assignments import assignments_bp
    from routes.submissions import submissions_bp
    from routes.peer_reviews import peer_reviews_bp, pending_reviews_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(classes_bp, url_prefix="/api/classes")

    # Nested: /api/classes/<class_id>/assignments
    app.register_blueprint(
        assignments_bp, url_prefix="/api/classes/<int:class_id>/assignments"
    )

    # Nested: /api/classes/<class_id>/assignments/<assignment_id>/submissions
    app.register_blueprint(
        submissions_bp,
        url_prefix="/api/classes/<int:class_id>/assignments/<int:assignment_id>/submissions",
    )

    # Nested: /api/classes/<cid>/assignments/<aid>/submissions/<sid>/peer-reviews
    app.register_blueprint(
        peer_reviews_bp,
        url_prefix="/api/classes/<int:class_id>/assignments/<int:assignment_id>/submissions/<int:submission_id>/peer-reviews",
    )

    # Standalone: /api/peer-reviews/pending
    app.register_blueprint(pending_reviews_bp, url_prefix="/api/peer-reviews")


def _register_error_handlers(app):
    """Global JSON error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# ──────────────────────────────────────────────
# Module-level app instance (used by gunicorn)
# ──────────────────────────────────────────────
app = create_app()

# ──────────────────────────────────────────────
# Run directly: python app.py
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
