"""Flask extensions initialization."""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Initialize extensions without app context - single instances
db = SQLAlchemy()
jwt = JWTManager()


def init_extensions(app):
    """Initialize extensions with Flask app."""
    db.init_app(app)
    jwt.init_app(app)


def init_jwt_loaders(app):
    """Initialize JWT token blocklist loader."""
    from app.models.revoked_token import RevokedToken
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return RevokedToken.query.filter_by(jti=jwt_payload["jti"]).first() is not None

