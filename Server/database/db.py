# server/database/db.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)  # internal DB ID
    unique_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    keys = relationship("PublicKey", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password):
         return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PublicKey(db.Model):
    __tablename__ = 'public_keys'
    id = db.Column(db.Integer, primary_key=True)  # per-user key id (auto increment)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    # This field stores the unique composite key identifier like "userID-keyID"
    key_uid = db.Column(db.String(100), unique=True, nullable=False)

    owner = relationship("User", back_populates="keys")


class EncryptedMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80), nullable=False)
    recipient = db.Column(db.String(80), nullable=False)
    encrypted_message = db.Column(db.Text, nullable=False)
    key_uid = db.Column(db.String(100), nullable=False)  # new field
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
