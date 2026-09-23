"""Message service."""

from app.extensions import db
from app.models import EncryptedMessage, PublicKey, User


class MessageService:
    """Service for message operations."""

    @staticmethod
    def get_user_list(current_username):
        """Get list of users to send messages to."""
        users = User.query.filter(User.username != current_username).all()
        return [{"username": user.username} for user in users]

    @staticmethod
    def send_message(sender_username, recipient_username, encrypted_message, key_uid):
        """Send an encrypted message."""
        sender = User.query.filter_by(username=sender_username).first()
        recipient = User.query.filter_by(username=recipient_username).first()

        # Basic validations
        if not recipient_username or not encrypted_message or not key_uid:
            return None, "Recipient, message, and key_uid are required", 400

        if len(encrypted_message.strip()) == 0:
            return None, "Message cannot be empty", 400

        if len(encrypted_message) > 5000:
            return None, "Message too long", 413

        if sender_username == recipient_username:
            return None, "Cannot send message to yourself", 400

        if not recipient:
            return None, "Recipient user does not exist", 404

        # Validate public key UID
        key_entry = PublicKey.query.filter_by(key_uid=key_uid, user_id=recipient.unique_id).first()
        if not key_entry:
            return None, "Invalid or mismatched key_uid for recipient", 400

        # Generate per-recipient message_uid
        message_uid = recipient.message_counter
        recipient.message_counter += 1

        recipient.current_messages += 1

        # Create and store message
        message = EncryptedMessage(
            message_uid=str(message_uid),
            sender_id=sender.unique_id,
            recipient_id=recipient.unique_id,
            encrypted_message=encrypted_message,
            key_uid=key_uid
        )

        db.session.add(message)
        db.session.commit()

        return message, None, None

    @staticmethod
    def get_user_inbox(user):
        """Get all messages for a user."""
        messages = EncryptedMessage.query.filter_by(recipient_id=user.unique_id)\
                                         .order_by(EncryptedMessage.timestamp.desc()).all()
        return messages

    @staticmethod
    def get_message_by_uid(user, message_uid):
        """Get a specific message by its UID."""
        msg = EncryptedMessage.query.filter_by(
            recipient_id=user.unique_id,
            message_uid=message_uid
        ).first()
        return msg

    @staticmethod
    def delete_message(user, message_uid):
        """Delete a message by its UID."""
        message = EncryptedMessage.query.filter_by(
            recipient_id=user.unique_id,
            message_uid=message_uid
        ).first()

        if not message:
            return False, "Message not found"

        db.session.delete(message)
        user.current_messages = max(user.current_messages - 1, 0)
        db.session.commit()
        return True, None
