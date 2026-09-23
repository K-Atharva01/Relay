"""Message routes."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.services import auth as auth_service
from app.services import keys as key_service
from app.services import messages as message_service
from app.utils.request import get_json_object, get_str

message_bp = Blueprint("message", __name__)

# Inbox pagination defaults and bounds.
DEFAULT_INBOX_LIMIT = 50
MAX_INBOX_LIMIT = 100


def _message_json(msg):
    return {
        "message_uid": msg.message_uid,
        "sender": msg.sender.username,
        "message": msg.encrypted_message,
        "key_uid": msg.key_uid,
        "timestamp": msg.timestamp.isoformat(),
        "expires_at": msg.expires_at.isoformat() if msg.expires_at else None,
    }


def _get_message_uid(data):
    """Return message_uid as a string. Legacy rows used integer-like uids, so accept both."""
    value = data.get("message_uid")
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value if isinstance(value, str) else None


@message_bp.route("/sendTo", methods=["GET"])
@jwt_required()
def lookup_user():
    """Exact-username lookup. Relay does not expose a full user directory."""
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username query parameter is required"}), 400
    if len(username) > 50:
        return jsonify({"error": "username must be at most 50 characters"}), 400
    if not auth_service.get_user_by_username(username):
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": username}), 200


@message_bp.route("/send", methods=["POST"])
@jwt_required()
def send_message():
    """Send an encrypted message."""
    data = get_json_object()
    recipient_username = get_str(data, "recipient")
    encrypted_message = get_str(data, "message")
    key_uid = get_str(data, "key_uid")

    # Basic validations
    if not recipient_username or not encrypted_message or not key_uid:
        return jsonify({"error": "Recipient, message, and key_uid are required"}), 400

    if len(encrypted_message.strip()) == 0:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(encrypted_message) > 5000:
        return jsonify({"error": "Message too long"}), 413

    if current_user.username == recipient_username:
        return jsonify({"error": "Cannot send message to yourself"}), 400

    recipient = auth_service.get_user_by_username(recipient_username)
    if not recipient:
        return jsonify({"error": "Recipient user does not exist"}), 404

    if not key_service.get_user_key(recipient, key_uid):
        return jsonify({"error": "Invalid or mismatched key_uid for recipient"}), 400

    message, error = message_service.send_message(
        current_user, recipient, encrypted_message, key_uid,
        ttl_days=current_app.config["MESSAGE_TTL_DAYS"],
        max_inbox=current_app.config["MAX_INBOX_MESSAGES"],
    )
    if error:
        return jsonify({"error": error}), 409

    return jsonify({"message": "Message sent successfully", "message_uid": message.message_uid}), 200


@message_bp.route("/inbox", methods=["GET"])
@jwt_required()
def get_messages():
    """Get a page of the authenticated user's inbox, newest first."""
    limit_raw = request.args.get("limit", str(DEFAULT_INBOX_LIMIT))
    offset_raw = request.args.get("offset", "0")

    if not limit_raw.isdigit() or not offset_raw.isdigit():
        return jsonify({
            "error": "limit and offset must be non-negative integers"
        }), 400

    limit = int(limit_raw)
    offset = int(offset_raw)
    if limit < 1 or limit > MAX_INBOX_LIMIT:
        return jsonify({
            "error": f"limit must be between 1 and {MAX_INBOX_LIMIT}"
        }), 400

    message_service.purge_expired(current_user)
    total, messages = message_service.get_inbox(current_user, limit, offset)

    return jsonify({
        "messages": [_message_json(msg) for msg in messages],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@message_bp.route("/getMessageById", methods=["POST"])
@jwt_required()
def get_message_by_uid():
    """Get a specific message by its UID."""
    message_uid = _get_message_uid(get_json_object())

    if not message_uid:
        return jsonify({"error": "Missing message_uid parameter"}), 400

    msg = message_service.get_message(current_user, message_uid)

    if not msg:
        return jsonify({"error": "Message not found"}), 404

    return jsonify(_message_json(msg)), 200


@message_bp.route("/inbox/deleteMessage", methods=["POST"])
@jwt_required()
def delete_message_by_uid():
    """Delete a message by its UID."""
    message_uid = _get_message_uid(get_json_object())

    if not message_uid:
        return jsonify({"error": "Missing message_uid parameter"}), 400

    if not message_service.delete_message(current_user, message_uid):
        return jsonify({"error": "Message not found"}), 404

    return jsonify({"message": "Message deleted successfully"}), 200
