"""
app.py - Application factory for the College Management System Flask backend.

Usage:
    from app import create_app
    app = create_app("production")
"""

import os
import logging
from datetime import datetime

from flask import Flask, jsonify, render_template, redirect, url_for, request
from flask_login import current_user

from config import config_map, ProductionConfig
from extensions import db, migrate, login_manager, csrf, mail


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory.

    Args:
        config_name: One of 'development', 'production', or 'default'.
                     Falls back to the FLASK_ENV environment variable, then
                     'default' (DevelopmentConfig).

    Returns:
        A fully configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=False)

    # ------------------------------------------------------------------ #
    # Load configuration
    # ------------------------------------------------------------------ #
    cfg_class = config_map.get(config_name, config_map["default"])
    app.config.from_object(cfg_class)

    # In production, validate that all required env vars are set
    if config_name == "production":
        ProductionConfig.validate()

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    _configure_logging(app)

    # ------------------------------------------------------------------ #
    # Initialise extensions
    # ------------------------------------------------------------------ #
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # ------------------------------------------------------------------ #
    # User loader for Flask-Login
    # ------------------------------------------------------------------ #
    from models.user import User  # noqa: import inside factory to avoid circular deps

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ------------------------------------------------------------------ #
    # Register blueprints
    # ------------------------------------------------------------------ #
    _register_blueprints(app)

    # ------------------------------------------------------------------ #
    # Register error handlers
    # ------------------------------------------------------------------ #
    _register_error_handlers(app)

    # ------------------------------------------------------------------ #
    # Jinja2 context processors
    # ------------------------------------------------------------------ #
    @app.context_processor
    def inject_globals():
        return {
            "current_user": current_user,
            "datetime": datetime,
            "now": datetime.utcnow(),
            "app_name": "College Management System",
        }

    # ------------------------------------------------------------------ #
    # Shell context – `flask shell` convenience
    # ------------------------------------------------------------------ #
    @app.shell_context_processor
    def make_shell_context():
        return {
            "db": db,
            "app": app,
        }

    app.logger.info("Application created with config: %s", config_name)
    return app


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _configure_logging(app: Flask) -> None:
    """Set up structured logging for the application."""
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    app.logger.setLevel(log_level)


def _register_blueprints(app: Flask) -> None:
    """Import and register all application blueprints."""

    # Root redirect
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            role = current_user.role.name if current_user.role else ""
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif role == "faculty":
                return redirect(url_for("faculty.dashboard"))
            elif role == "student":
                return redirect(url_for("student.dashboard"))
        return redirect(url_for("auth.login"))

    # Auth
    from routes.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Admin
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Faculty
    from routes.faculty import faculty_bp
    app.register_blueprint(faculty_bp, url_prefix="/faculty")

    # Student
    from routes.students import student_bp
    app.register_blueprint(student_bp, url_prefix="/student")

    # Attendance
    from routes.attendance import attendance_bp
    app.register_blueprint(attendance_bp, url_prefix="/attendance")

    # Examinations
    from routes.examinations import exam_bp
    app.register_blueprint(exam_bp, url_prefix="/exam")

    # Results
    from routes.results import results_bp
    app.register_blueprint(results_bp, url_prefix="/results")

    # Fees
    from routes.fees import fees_bp
    app.register_blueprint(fees_bp, url_prefix="/fees")

    # Assignments
    from routes.assignments import assignments_bp
    app.register_blueprint(assignments_bp, url_prefix="/assignments")

    # Notifications
    from routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    app.logger.debug("All blueprints registered successfully.")


def _register_error_handlers(app: Flask) -> None:
    """Register HTTP error handlers that return JSON for API calls, HTML otherwise."""

    def _wants_json() -> bool:
        """Return True when the client prefers a JSON response."""
        best = request.accept_mimetypes.best_match(["application/json", "text/html"])
        return best == "application/json" or request.path.startswith("/api/")

    @app.errorhandler(400)
    def bad_request(error):
        if _wants_json():
            return jsonify({"error": "Bad Request", "message": str(error), "status": 400}), 400
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(
            "403 Forbidden: %s %s – user=%s",
            request.method,
            request.path,
            current_user.get_id() if current_user else "anonymous",
        )
        if _wants_json():
            return jsonify({"error": "Forbidden", "message": "You do not have permission to perform this action.", "status": 403}), 403
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        if _wants_json():
            return jsonify({"error": "Not Found", "message": "The requested resource was not found.", "status": 404}), 404
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if _wants_json():
            return jsonify({"error": "Method Not Allowed", "message": str(error), "status": 405}), 405
        return render_template("errors/405.html", error=error), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        # Roll back any failed transaction to leave the DB in a clean state
        try:
            db.session.rollback()
        except Exception:
            pass
        app.logger.exception("500 Internal Server Error: %s %s", request.method, request.path)
        if _wants_json():
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later.", "status": 500}), 500
        return render_template("errors/500.html", error=error), 500


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    _env = os.environ.get("FLASK_ENV", "development")
    _debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    _port = int(os.environ.get("PORT", 5000))
    _host = os.environ.get("HOST", "0.0.0.0")

    application = create_app(_env)
    application.run(host=_host, port=_port, debug=_debug)
