# server/database/db.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint # Import UniqueConstraint explicitly
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone # NEW: Import datetime and timezone for timestamp defaults
from flask_migrate import Migrate


db = SQLAlchemy()

# NEW: Initialize Flask-Migrate object here. Its init_app will be called in create_app.
migrate = Migrate()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True) 
    unique_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # current_jti: Stores the JTI of the user's currently active session, useful for
    # associating ephemeral keys or enforcing single session.
    current_jti = db.Column(db.String(120), nullable=True) 
    
    # Optional: Fields for tracking current active long-term certificate (e.g., if multiple exist)
    # This could be a FK to PublicKey.id where key_type='identity'
    # current_identity_key_id = db.Column(db.Integer, db.ForeignKey('public_keys.id'), nullable=True)

    message_counter = db.Column(db.Integer, default=1)   
    current_messages = db.Column(db.Integer, default=0)

    # Relationship to PublicKey model: User can have multiple public keys (ephemeral, identity)
    keys = relationship("PublicKey", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class PublicKey(db.Model):
    __tablename__ = 'public_keys'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    public_key_pem = db.Column(db.Text, nullable=False)
    
    key_type = db.Column(db.String(10), nullable=False) 
    
    jti = db.Column(db.String(120), nullable=True) 

    timestamp = db.Column(db.DateTime, server_default=db.func.now()) # This will use UTC thanks to app.py config
    # For more explicit timezone handling, consider: default=lambda: datetime.now(timezone.utc)

    key_uid = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4())) 

    owner = relationship("User", back_populates="keys")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'key_uid', name='unique_user_key_uid'),
        # Example for ensuring only one 'identity' key_type per user (for PostgreSQL using a partial index)
        # db.UniqueConstraint('user_id', 'key_type', name='unique_active_identity_key',
        #                     postgresql_where=db.Column('key_type') == 'identity'),
    )


class EncryptedMessage(db.Model):
    __tablename__ = 'encrypted_messages'

    id = db.Column(db.Integer, primary_key=True)
    message_uid = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))

    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    encrypted_content = db.Column(db.Text, nullable=False)
    
    recipient_key_uid = db.Column(db.String(36), nullable=False) 
    
    sender_signature = db.Column(db.Text, nullable=False) 
    
    sender_public_identity_key_uid = db.Column(db.String(36), nullable=False) 
    
    timestamp = db.Column(db.DateTime, server_default=db.func.now()) # This will use UTC
    is_opened = db.Column(db.Boolean, default=False, nullable=False) 

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="inbox")

    __table_args__ = (
        UniqueConstraint('recipient_id', 'message_uid', name='unique_recipient_message_uid'),
    )


class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now()) # This will use UTC

    @classmethod
    def is_jti_blocklisted(cls, jti):
        """Checks if a JTI is present in the revoked tokens list."""
        return cls.query.filter_by(jti=jti).first() is not None