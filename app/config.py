import os
from datetime import timedelta


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///secure_exchange.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    # Revocation uses the v4 token_in_blocklist_loader (app/extensions.py);
    # the removed 3.x JWT_BLACKLIST_* settings are ignored by 4.x.
    
    # Security
    PROPAGATE_EXCEPTIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size

    # Message retention: new messages expire after MESSAGE_TTL_DAYS
    # (0 disables expiry). Rows that predate expires_at never expire.
    MESSAGE_TTL_DAYS = int(os.environ.get("MESSAGE_TTL_DAYS", "30"))
    # Per-recipient stored-message cap enforced on send (0 disables the cap).
    MAX_INBOX_MESSAGES = int(os.environ.get("MAX_INBOX_MESSAGES", "1000"))
    
    # URL scheme for generating URLs
    PREFERRED_URL_SCHEME = "http"  # Change to "https" in production with TLS

    # Rate limiting (Flask-Limiter)
    RATELIMIT_STORAGE_URI = "memory://"
    # Moving window avoids request bursts straddling fixed window boundaries.
    RATELIMIT_STRATEGY = "moving-window"


class DevelopmentConfig(Config):
    """Development configuration."""
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"


class ProductionConfig(Config):
    """Production configuration."""
    FLASK_DEBUG = False
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_secure_exchange.db"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    PROPAGATE_EXCEPTIONS = True
    # Tests create many users and logins from one address; rate-limit tests
    # opt back in explicitly with their own app instance.
    RATELIMIT_ENABLED = False


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestingConfig
    return DevelopmentConfig

