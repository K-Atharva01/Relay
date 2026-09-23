"""Key management service."""

from app.extensions import db
from app.models import PublicKey


def add_key(user, public_key):
    """Store a public key for a user and return it."""
    key = PublicKey(user_id=user.unique_id, public_key=public_key, key_uid="temp")
    db.session.add(key)
    db.session.flush()  # Assigns key.id

    key.key_uid = f"{user.unique_id}-{key.id}"
    db.session.commit()
    return key


def get_user_keys(user):
    """Return all of a user's public keys, newest first."""
    return PublicKey.query.filter_by(user_id=user.unique_id)\
                          .order_by(PublicKey.timestamp.desc()).all()


def get_latest_key(user):
    """Return a user's newest public key, or None."""
    return PublicKey.query.filter_by(user_id=user.unique_id)\
                          .order_by(PublicKey.timestamp.desc()).first()


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
