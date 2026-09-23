"""Authentication service."""

from app.extensions import db
from app.models import User, RevokedToken


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def register_user(name, username, password, phone, email):
        """Register a new user."""
        # Check if user already exists
        existing = User.query.filter_by(username=username, phone=phone, email=email).first()
        if existing:
            return None, "User already exists"

        new_user = User(
            name=name,
            username=username,
            phone=phone,
            email=email,
            password_hash=User.set_password(password)
        )

        db.session.add(new_user)
        db.session.commit()
        return new_user, None

    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user and return user object if valid."""
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return None
        return user

    @staticmethod
    def revoke_previous_token(user):
        """Revoke previous JWT token if exists."""
        if user.current_jti:
            revoked = RevokedToken(jti=user.current_jti)
            db.session.add(revoked)

    @staticmethod
    def update_user_token_jti(user, new_jti):
        """Update user's current JWT ID."""
        user.current_jti = new_jti
        db.session.commit()

    @staticmethod
    def logout_token(jti):
        """Revoke a token."""
        if not RevokedToken.query.filter_by(jti=jti).first():
            revoked_token = RevokedToken(jti=jti)
            db.session.add(revoked_token)
            db.session.commit()
            return True
        return False
