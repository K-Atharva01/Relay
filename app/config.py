import os
from datetime import timedelta


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///secure_exchange.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access"]
    
    # Security
    PROPAGATE_EXCEPTIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    
    # URL scheme for generating URLs
    PREFERRED_URL_SCHEME = "http"  # Change to "https" in production with TLS


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


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestingConfig
    return DevelopmentConfig

