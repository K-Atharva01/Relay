"""Routes package."""

from app.routes.auth import auth_bp
from app.routes.keys import key_bp
from app.routes.messages import message_bp

__all__ = ["auth_bp", "key_bp", "message_bp"]
