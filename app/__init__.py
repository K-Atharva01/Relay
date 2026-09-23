"""Relay Flask Application.

This module provides the create_app factory function for creating
Flask application instances.
"""

from flask import Flask, jsonify
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from app.config import get_config
from app.extensions import db, jwt, init_extensions, init_jwt_loaders, init_limiter
from app.routes import auth_bp, key_bp, message_bp


def _migrate_schema(engine):
    """Apply small in-place schema migrations to existing databases.

    Intentional schema change: encrypted_messages.expires_at (message
    expiry). The column is nullable; rows that predate it never expire.
    """
    inspector = inspect(engine)
    if not inspector.has_table("encrypted_messages"):
        return
    columns = {column["name"]
               for column in inspector.get_columns("encrypted_messages")}
    if "expires_at" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE encrypted_messages ADD COLUMN expires_at DATETIME"
            ))

    # Intentional schema change: revocation moved to User.current_jti
    # (one session per user), so the append-only table is dropped.
    if inspector.has_table("revoked_tokens"):
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS revoked_tokens"))


def create_app(config_override=None):
    """Create and configure the Flask application.
    
    Args:
        config_override: Optional dictionary to override configuration.
        
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Apply any overrides
    if config_override:
        app.config.update(config_override)
    
    # Initialize extensions
    init_extensions(app)
    init_jwt_loaders(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(key_bp, url_prefix="/keys")
    app.register_blueprint(message_bp, url_prefix="/message")

    # Rate limiting must be initialized after blueprints are registered.
    init_limiter(app)
    
    # Error handlers
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        response = e.get_response()
        response.data = jsonify({
            "error": e.name,
            "description": e.description
        }).get_data()
        response.content_type = "application/json"
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception("Unhandled exception")
        return jsonify({
            "error": "Internal Server Error",
            "description": "An unexpected error occurred. Please try again later."
        }), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
        _migrate_schema(db.engine)
    
    return app


# For backwards compatibility
default_app = create_app()
