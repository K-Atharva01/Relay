"""Message service."""

from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import or_

from app.extensions import db
from app.models import EncryptedMessage


def _utcnow():
    """Naive UTC timestamp, consistent with SQLite's CURRENT_TIMESTAMP."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def purge_expired(user):
    """Delete a user's expired messages. Returns how many were removed."""
    count = EncryptedMessage.query.filter(
        EncryptedMessage.recipient_id == user.unique_id,
        EncryptedMessage.expires_at.isnot(None),
        EncryptedMessage.expires_at <= _utcnow(),
    ).delete(synchronize_session=False)

    if count:
        user.current_messages = max(user.current_messages - count, 0)
        db.session.commit()
    return count


def send_message(sender, recipient, encrypted_message, key_uid,
                 ttl_days=0, max_inbox=0):
    """Store an encrypted message for the recipient.

    Returns (message, None) on success, or (None, error) when the
    recipient's inbox is full.
    """
    # Expired messages no longer count against the inbox cap.
    purge_expired(recipient)

    if max_inbox and recipient.current_messages >= max_inbox:
        return None, "Recipient inbox is full"

    expires_at = None
    if ttl_days > 0:
        expires_at = _utcnow() + timedelta(days=ttl_days)

    recipient.current_messages += 1

    message = EncryptedMessage(
        # Opaque per-message identifier. UUIDs generated independently
        # cannot collide across concurrent sends the way a shared,
        # Python-side counter can.
        message_uid=str(uuid.uuid4()),
        sender_id=sender.unique_id,
        recipient_id=recipient.unique_id,
        encrypted_message=encrypted_message,
        key_uid=key_uid,
        expires_at=expires_at,
    )

    db.session.add(message)
    db.session.commit()
    return message, None


def get_inbox(user, limit, offset):
    """Return (total, page) of the user's non-expired messages, newest first.

    total counts all non-expired messages; page is limited to `limit`
    rows starting at `offset`. The id tiebreak keeps ordering stable
    when several messages share a second-precision timestamp.
    """
    base = EncryptedMessage.query.filter(
        EncryptedMessage.recipient_id == user.unique_id,
        or_(EncryptedMessage.expires_at.is_(None),
            EncryptedMessage.expires_at > _utcnow()),
    )
    total = base.count()
    page = (base.order_by(EncryptedMessage.timestamp.desc(),
                          EncryptedMessage.id.desc())
                .offset(offset)
                .limit(limit)
                .all())
    return total, page


def get_message(user, message_uid):
    """Return one of the user's non-expired messages, or None."""
    return EncryptedMessage.query.filter(
        EncryptedMessage.recipient_id == user.unique_id,
        EncryptedMessage.message_uid == message_uid,
        or_(EncryptedMessage.expires_at.is_(None),
            EncryptedMessage.expires_at > _utcnow()),
    ).first()


def delete_message(user, message_uid):
    """Delete one of the user's messages. Returns False if there is no such message."""
    message = get_message(user, message_uid)
    if not message:
        return False

    db.session.delete(message)
    user.current_messages = max(user.current_messages - 1, 0)
    db.session.commit()
    return True
