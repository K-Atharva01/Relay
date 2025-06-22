# server/database/db.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True) 
    unique_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    current_jti = db.Column(db.String(120), nullable=True)
    message_counter = db.Column(db.Integer, default=1)  
    current_messages = db.Column(db.Integer, default=0)


    keys = relationship("PublicKey", back_populates="owner", cascade="all, delete-orphan")

    def set_password(password):
         return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PublicKey(db.Model):
    __tablename__ = 'public_keys'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.unique_id'), nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    key_uid = db.Column(db.String(100), unique=True, nullable=False) #Composite-key

    owner = relationship("User", back_populates="keys")


class EncryptedMessage(db.Model):
    __tablename__ = 'encrypted_messages'

    id = db.Column(db.Integer, primary_key=True)
    message_uid = db.Column(db.String(100), nullable=False)

    sender_id = db.Column(db.Integer, db.ForeignKey('users.unique_id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.unique_id'), nullable=False)

    encrypted_message = db.Column(db.Text, nullable=False)
    key_uid = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="inbox")

    # Ensure message_uid is unique per recipient
    __table_args__ = (
        db.UniqueConstraint('recipient_id', 'message_uid', name='unique_recipient_message_uid'),
    )



class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
