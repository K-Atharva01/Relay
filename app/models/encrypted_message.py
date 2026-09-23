"""Encrypted message model."""

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.extensions import db


class EncryptedMessage(db.Model):
    """Encrypted message model for storing messages."""
    __tablename__ = "encrypted_messages"

    id = db.Column(db.Integer, primary_key=True)
    message_uid = db.Column(db.String(100), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey("users.unique_id"), nullable=False)
    recipient_id = db.Column(db.String(36), db.ForeignKey("users.unique_id"), nullable=False)
    encrypted_message = db.Column(db.Text, nullable=False)
    key_uid = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    # When this ciphertext expires (naive UTC). NULL = never expires
    # (messages that predate the column, or MESSAGE_TTL_DAYS=0).
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="inbox")

    # Ensure message_uid is unique per recipient
    __table_args__ = (
        UniqueConstraint("recipient_id", "message_uid", name="unique_recipient_message_uid"),
    )

