"""Key management service."""

from app.extensions import db
from app.models import PublicKey, User


class KeyService:
    """Service for public key operations."""

    @staticmethod
    def get_user_by_username(username):
        """Get user by username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def upload_key(user, public_key):
        """Upload a public key for a user."""
        try:
            # Step 1: Insert with placeholder key_uid
            placeholder_key = PublicKey(user_id=user.unique_id, public_key=public_key, key_uid="temp")
            db.session.add(placeholder_key)
            db.session.flush()  # Get the auto-generated id

            # Step 2: Generate key_uid using user.id and key.id
            placeholder_key.key_uid = f"{user.unique_id}-{placeholder_key.id}"
            db.session.commit()

            return placeholder_key, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_user_keys(user):
        """Get all public keys for a user."""
        return PublicKey.query.filter_by(user_id=user.unique_id).order_by(PublicKey.timestamp.desc()).all()

    @staticmethod
    def get_latest_key_for_user(user):
        """Get the latest public key for a user."""
        return PublicKey.query.filter_by(user_id=user.unique_id)\
                             .order_by(PublicKey.timestamp.desc()).first()

    @staticmethod
    def delete_key(user, key_uid):
        """Delete a public key for a user."""
        key = PublicKey.query.filter_by(key_uid=key_uid, user_id=user.unique_id).first()
        if not key:
            return False, "Key not found or does not belong to the user"

        db.session.delete(key)
        db.session.commit()
        return True, None
