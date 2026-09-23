"""Key management routes."""

from flask import Blueprint, jsonify
from flask_jwt_extended import (
    current_user,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_limiter.util import get_remote_address
from jwt.exceptions import PyJWTError

from app.extensions import limiter
from app.services import auth as auth_service
from app.services import keys as key_service
from app.utils.keys import validate_public_key
from app.utils.request import get_json_object, get_str

key_bp = Blueprint("keys", __name__)


def _add_key_rate_limit_key():
    """Per-account rate-limit key: token's username, else client IP."""
    try:
        verify_jwt_in_request()
        return f"user:{get_jwt_identity()}"
    except (JWTExtendedException, PyJWTError):
        # jwt_required() rejects the request; this key is never used for a real attempt.
        return f"ip:{get_remote_address()}"


def _count_wrong_password(response):
    """Only wrong passwords consume the per-account quota."""
    return response.status_code == 403


@key_bp.route("/addKey", methods=["POST"])
@limiter.limit(
    "5 per minute",
    key_func=_add_key_rate_limit_key,
    deduct_when=_count_wrong_password,
)
@jwt_required()
def upload_key():
    """Upload a public key for the authenticated user.

    Requires the account password as well as the JWT, so a stolen token alone
    cannot replace the key that senders encrypt to. This does not stop a
    malicious server or anyone with database write access from substituting a
    key; that needs client-side fingerprint checks.
    """
    data = get_json_object()
    public_key = get_str(data, "public_key")
    password = get_str(data, "password")

    if not public_key:
        return jsonify({"error": "Public key is required"}), 400

    if not password:
        return jsonify({"error": "Password is required"}), 400

    if not current_user.check_password(password):
        return jsonify({"error": "Invalid password"}), 403

    key_error = validate_public_key(public_key)
    if key_error:
        return jsonify({"error": key_error}), 400

    key = key_service.add_key(current_user, public_key)

    return jsonify({"message": "Public key uploaded successfully", "key_uid": key.key_uid}), 201


@key_bp.route("/getAllKeys", methods=["GET"])
@jwt_required()
def get_keys():
    """Get all public keys for the authenticated user."""
    keys = key_service.get_user_keys(current_user)

    key_list = [{
        "key_uid": key.key_uid,
        "public_key": key.public_key,
        "timestamp": key.timestamp.isoformat()
    } for key in keys]

    return jsonify({
        "username": current_user.username,
        "public_keys": key_list
    }), 200


@key_bp.route("/fetchPublicKey", methods=["POST"])
@jwt_required()
def get_recipient_public_key():
    """Fetch the latest public key for a recipient."""
    recipient_username = get_str(get_json_object(), "username")

    if not recipient_username:
        return jsonify({"error": "Recipient username required"}), 400

    recipient = auth_service.get_user_by_username(recipient_username)
    if not recipient:
        return jsonify({"error": "Recipient not found"}), 404

    latest_key = key_service.get_latest_key(recipient)

    if not latest_key:
        return jsonify({"error": "No public key found for recipient"}), 404

    return jsonify({
        "username": recipient.username,
        "key_uid": latest_key.key_uid,
        "public_key": latest_key.public_key
    }), 200


@key_bp.route("/deleteKey", methods=["POST"])
@jwt_required()
def delete_key():
    """Delete a public key for the authenticated user."""
    key_uid = get_str(get_json_object(), "key_uid")

    if not key_uid:
        return jsonify({"error": "key_uid is required"}), 400

    if not key_service.delete_key(current_user, key_uid):
        return jsonify({"error": "Key not found or does not belong to the user"}), 404

    return jsonify({"message": "Key deleted successfully"}), 200
