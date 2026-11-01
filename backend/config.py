"""
config.py - Application configuration classes for the College Management System.

Loads all settings from environment variables for 12-factor compliance.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file if present (development convenience)
load_dotenv()


def _build_db_uri() -> str:
    """Construct the MySQL connection URI from individual env variables."""
    host = os.environ.get("DATABASE_HOST", "localhost")
    port = os.environ.get("DATABASE_PORT", "3306")
    name = os.environ.get("DATABASE_NAME", "college_management")
    user = os.environ.get("DATABASE_USER", "root")
    password = os.environ.get("DATABASE_PASSWORD", "")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    """Base configuration shared by all environments."""

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    WTF_CSRF_ENABLED: bool = True

    # ------------------------------------------------------------------ #
    # Session
    # ------------------------------------------------------------------ #
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", _build_db_uri())
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
    }

    # ------------------------------------------------------------------ #
    # AWS / S3
    # ------------------------------------------------------------------ #
    AWS_REGION: str = os.environ.get("AWS_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "college-management-bucket")

    # ------------------------------------------------------------------ #
    # File uploads
    # ------------------------------------------------------------------ #
    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set = {
        "png", "jpg", "jpeg", "gif", "webp",  # images
        "pdf",                                  # documents
        "doc", "docx",                          # Word
        "xls", "xlsx",                          # Excel
        "ppt", "pptx",                          # PowerPoint
        "txt", "csv",                           # plain text
        "zip", "tar", "gz",                     # archives
    }

    # ------------------------------------------------------------------ #
    # Mail (optional – configure for notifications)
    # ------------------------------------------------------------------ #
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS: bool = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@college.edu")

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """Development-specific configuration. Never use in production."""

    DEBUG: bool = True
    TESTING: bool = False
    WTF_CSRF_ENABLED: bool = False  # Easier API testing in dev

    # Use a local MySQL or SQLite fallback for quick bootstrapping
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"mysql+pymysql://root:@localhost:3306/college_management_dev?charset=utf8mb4",
    )

    # Tighter pool for local dev
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 20,
        "pool_recycle": 900,
        "pool_pre_ping": True,
    }

    SESSION_COOKIE_SECURE: bool = False
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(Config):
    """Production configuration – all sensitive values MUST come from env."""

    DEBUG: bool = False
    TESTING: bool = False
    WTF_CSRF_ENABLED: bool = True
    SESSION_COOKIE_SECURE: bool = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "WARNING")

    @classmethod
    def validate(cls) -> None:
        """Raise RuntimeError if critical production variables are missing."""
        required = [
            "SECRET_KEY",
            "DATABASE_HOST",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "S3_BUCKET_NAME",
        ]
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            raise RuntimeError(
                f"Missing required production environment variables: {missing}"
            )


# ------------------------------------------------------------------ #
# Config registry – used by create_app()
# ------------------------------------------------------------------ #
config_map: dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
