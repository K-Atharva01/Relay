"""Flask extensions initialization."""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions without app context - single instances
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def init_extensions(app):
    """Initialize extensions with Flask app."""
    db.init_app(app)
    jwt.init_app(app)


def init_limiter(app):
    """Initialize rate limiting (call after blueprints are registered)."""
    limiter.init_app(app)


def init_jwt_loaders(app):
    """Initialize JWT revocation and user lookup loaders."""
    from app.models.user import User

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        # One session per user: a token is valid only while its jti is
        # the user's current session. start_session rotates current_jti
        # on login and end_session clears it on logout, so no separate
        # (ever-growing) revocation table is needed.
        user = User.query.filter_by(username=jwt_payload["sub"]).first()
        return user is None or user.current_jti != jwt_payload["jti"]

    # The JWT identity is the username. Resolving it here means protected
    # routes get the User via flask_jwt_extended.current_user, and a token
    # for a user that no longer exists is rejected with 401.
    @jwt.user_lookup_loader
    def load_user(jwt_header, jwt_payload):
        return User.query.filter_by(username=jwt_payload["sub"]).one_or_none()

