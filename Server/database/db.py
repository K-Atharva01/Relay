# server/database/db.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint # Import UniqueConstraint explicitly
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True) 
    # unique_id remains as a public-facing identifier, but internal FKs will link to 'id'
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

    # --- CORRECTED: set_password method ---
    # It must be an instance method (takes 'self') and assigns to self.password_hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PublicKey(db.Model):
    __tablename__ = 'public_keys'
    id = db.Column(db.Integer, primary_key=True)
    
    # --- CORRECTED: Foreign Key type match ---
    # user_id now correctly links to users.id (Integer primary key)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # --- ENHANCED: Renamed for clarity and supports both raw keys and certificates ---
    # Stores the PEM-encoded public key (for ephemeral) or the signed X.509 certificate (for identity)
    public_key_pem = db.Column(db.Text, nullable=False)
    
    # --- ENHANCED: New column to distinguish key type ---
    # 'ephemeral' for session keys, 'identity' for long-term permanent keys/certificates
    key_type = db.Column(db.String(10), nullable=False) 
    
    # --- ENHANCED: JTI for ephemeral keys ---
    # Links an ephemeral key to a specific JWT session for lifecycle management (nullable for identity keys)
    jti = db.Column(db.String(120), nullable=True) 

    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    # --- ENHANCED: key_uid for universal identification ---
    # Changed to String(36) for UUID standard. Not unique on its own column.
    # Uniqueness is enforced by a composite constraint (see __table_args__)
    key_uid = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4())) 

    owner = relationship("User", back_populates="keys")

    # --- ENHANCED: Composite Unique Constraint ---
    # Ensures a user has a unique key_uid for a specific key_type
    # Example: A user typically has one 'identity' key_uid active, and one 'ephemeral' key_uid per JTI.
    # You might refine this further based on your exact active key rules (e.g., only one active 'identity' key)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'key_uid', name='unique_user_key_uid'),
        # Example for ensuring only one 'identity' key_type per user (for PostgreSQL using a partial index)
        # db.UniqueConstraint('user_id', 'key_type', name='unique_active_identity_key',
        #                     postgresql_where=db.Column('key_type') == 'identity'),
    )


class EncryptedMessage(db.Model):
    __tablename__ = 'encrypted_messages'

    id = db.Column(db.Integer, primary_key=True)
    # --- ENHANCED: message_uid for UUID standard ---
    message_uid = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))

    # --- CORRECTED: Foreign Keys now link to users.id (Integer) ---
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # --- RENAMED for clarity ---
    encrypted_content = db.Column(db.Text, nullable=False)
    
    # --- RENAMED for clarity and consistency with PublicKey.key_uid ---
    # This is the key_uid of the recipient's public key (ephemeral or identity) used for encryption
    recipient_key_uid = db.Column(db.String(36), nullable=False) 
    
    # --- ENHANCED: New column for Digital Signature ---
    # The digital signature of the plaintext message, generated by the sender's long-term private key
    sender_signature = db.Column(db.Text, nullable=False) 
    
    # --- ENHANCED: New column for Sender's Public Identity Key UID ---
    # This identifies the sender's long-term identity certificate used for signature verification
    sender_public_identity_key_uid = db.Column(db.String(36), nullable=False) 
    
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    # --- ENHANCED: New column to track message status ---
    is_opened = db.Column(db.Boolean, default=False, nullable=False) 

    # Relationships
    # Ensure foreign_keys explicitly state which column to link from the current model
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="inbox")

    __table_args__ = (
        UniqueConstraint('recipient_id', 'message_uid', name='unique_recipient_message_uid'),
    )


class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())