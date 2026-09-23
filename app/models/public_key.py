"""Public key model."""

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.extensions import db


class PublicKey(db.Model):
    """Public key model for storing user public keys."""
    __tablename__ = "public_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.unique_id"), nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    key_uid = db.Column(db.String(100), unique=True, nullable=False)

    owner = relationship("User", back_populates="keys")

