"""Key management service."""

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.extensions import db
from app.models import PublicKey

# Maximum accepted public key size in bytes. Real PEM keys are a few KB;
# this blocks oversized blobs well below the global MAX_CONTENT_LENGTH.
MAX_PUBLIC_KEY_BYTES = 16 * 1024

# Minimum accepted RSA modulus size in bits.
MIN_RSA_BITS = 2048


def validate_public_key(pem):
    """Return an error message if this PEM public key is unacceptable, else None.

    Accepted keys are PEM-encoded (SubjectPublicKeyInfo) RSA public keys
    of at least MIN_RSA_BITS bits.
    """
    if len(pem.encode("utf-8")) > MAX_PUBLIC_KEY_BYTES:
        return f"Public key is too large (maximum {MAX_PUBLIC_KEY_BYTES} bytes)"

    try:
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
    except UnsupportedAlgorithm:
        return "Public key uses an unsupported algorithm"
    except ValueError:
        return "Public key must be a valid PEM-encoded public key"

    if not isinstance(key, rsa.RSAPublicKey):
        return "Public key must be an RSA public key"

    if key.key_size < MIN_RSA_BITS:
        return f"RSA public key must be at least {MIN_RSA_BITS} bits"

    return None


def add_key(user, public_key):
    """Store a public key for a user and return it."""
    key = PublicKey(user_id=user.unique_id, public_key=public_key, key_uid="temp")
    db.session.add(key)
    db.session.flush()  # Assigns key.id

    key.key_uid = f"{user.unique_id}-{key.id}"
    db.session.commit()
    return key


def get_user_keys(user):
    """Return all of a user's public keys, newest first.

    The id tiebreak keeps the order deterministic when several keys share
    a second-precision timestamp.
    """
    return PublicKey.query.filter_by(user_id=user.unique_id)\
                          .order_by(PublicKey.timestamp.desc(),
                                    PublicKey.id.desc()).all()


def get_latest_key(user):
    """Return a user's newest public key, or None."""
    return PublicKey.query.filter_by(user_id=user.unique_id)\
                          .order_by(PublicKey.timestamp.desc(),
                                    PublicKey.id.desc()).first()


def get_user_key(user, key_uid):
    """Return the key with this key_uid if it belongs to the user, or None."""
    return PublicKey.query.filter_by(key_uid=key_uid, user_id=user.unique_id).first()


def delete_key(user, key_uid):
    """Delete one of the user's keys. Returns False if the user has no such key."""
    key = get_user_key(user, key_uid)
    if not key:
        return False

    db.session.delete(key)
    db.session.commit()
    return True
