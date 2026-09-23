"""User model."""

import uuid
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    """User model for authentication and messaging."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    current_jti = db.Column(db.String(120), nullable=True)
    # Legacy per-recipient sequence counter. message_uid now uses UUIDs;
    # the column is kept to avoid a schema migration.
    message_counter = db.Column(db.Integer, default=1)
    current_messages = db.Column(db.Integer, default=0)

    keys = relationship("PublicKey", back_populates="owner", cascade="all, delete-orphan")

    @staticmethod
    def set_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

