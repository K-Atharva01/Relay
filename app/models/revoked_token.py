"""Revoked token model."""

from sqlalchemy import String, DateTime

from app.extensions import db


class RevokedToken(db.Model):
    """Revoked token model for JWT token blacklisting."""
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

