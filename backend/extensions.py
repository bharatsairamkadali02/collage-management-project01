"""
extensions.py - Initialise Flask extensions in isolation (no app context).

All extensions are imported and configured in app.py via init_app() to
avoid circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# ---------------------------------------------------------------------- #
# SQLAlchemy – primary ORM / database layer
# ---------------------------------------------------------------------- #
db = SQLAlchemy()

# ---------------------------------------------------------------------- #
# Alembic migration support via Flask-Migrate
# ---------------------------------------------------------------------- #
migrate = Migrate()

# ---------------------------------------------------------------------- #
# Login / session management
# ---------------------------------------------------------------------- #
login_manager = LoginManager()
login_manager.login_view = "auth.login"          # redirect endpoint when @login_required fails
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

# ---------------------------------------------------------------------- #
# CSRF protection (Flask-WTF)
# ---------------------------------------------------------------------- #
csrf = CSRFProtect()

# ---------------------------------------------------------------------- #
# Email dispatch (Flask-Mail)
# ---------------------------------------------------------------------- #
mail = Mail()
