"""Relay Flask Application.

This module provides the create_app factory function for creating
Flask application instances.
"""

from flask import Flask, jsonify
from http.client import HTTPException

from app.config import get_config
from app.extensions import db, jwt, init_extensions, init_jwt_loaders
from app.routes import auth_bp, key_bp, message_bp


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
        return jsonify({
            "error": "Internal Server Error",
            "description": "An unexpected error occurred. Please try again later."
        }), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


# For backwards compatibility
default_app = create_app()
