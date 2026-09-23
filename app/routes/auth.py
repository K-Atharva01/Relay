"""Authentication routes."""

from flask import Blueprint, jsonify
from flask_jwt_extended import (
    create_access_token,
    current_user,
    get_jti,
    get_jwt,
    jwt_required,
)
from flask_limiter.util import get_remote_address

from app.extensions import limiter
from app.services import auth as auth_service
from app.utils.request import get_json_object, get_str

auth_bp = Blueprint("auth", __name__)

# Maximum lengths, kept in sync with the User model's String(n) columns.
# SQLite does not enforce these limits, so validate before touching the database.
FIELD_LIMITS = {
    "name": 100,
    "username": 50,
    "password": 1024,
    "phone": 15,
    "email": 100,
}

# Minimum password length enforced at registration.
MIN_PASSWORD_LENGTH = 12


def _login_rate_limit_key():
    """Per-account rate-limit key: submitted username, else client IP."""
    username = get_str(get_json_object(), "username")
    return f"user:{username}" if username else f"ip:{get_remote_address()}"


def _count_failed_login(response):
    """Only failed login attempts consume the per-account quota."""
    return response.status_code == 401


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register_user():
    """Register a new user."""

    data = get_json_object()

    name = get_str(data, "name")
    username = get_str(data, "username")
    password = get_str(data, "password")
    phone = get_str(data, "phone")
    email = get_str(data, "email")

    fields = {
        "name": name,
        "username": username,
        "password": password,
        "phone": phone,
        "email": email,
    }

    if not all(fields.values()):
        return jsonify({
            "error": "name, username, password, phone and email are required"
        }), 400

    # Whitespace-only values are missing values (password may contain spaces).
    if any(not value.strip() for key, value in fields.items() if key != "password"):
        return jsonify({
            "error": "name, username, phone and email cannot be blank"
        }), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "error": f"password must be at least {MIN_PASSWORD_LENGTH} characters"
        }), 400

    for field, value in fields.items():
        if len(value) > FIELD_LIMITS[field]:
            return jsonify({
                "error": f"{field} must be at most {FIELD_LIMITS[field]} characters"
            }), 400

    new_user, error = auth_service.register_user(
        name=name,
        username=username,
        password=password,
        phone=phone,
        email=email,
    )

    if error:
        return jsonify({"error": error}), 409

    return jsonify({
        "message": "User registered successfully"
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("30 per minute")
@limiter.limit(
    "5 per minute",
    key_func=_login_rate_limit_key,
    deduct_when=_count_failed_login,
)
def login():
    """Login user and return JWT token."""

    data = get_json_object()

    username = get_str(data, "username")
    password = get_str(data, "password")

    if not all([username, password]):
        return jsonify({
            "error": "Username and password required"
        }), 400

    user = auth_service.authenticate_user(username, password)

    if not user:
        return jsonify({
            "error": "Invalid credentials"
        }), 401

    access_token = create_access_token(identity=username)

    # Revokes the previous token, if any: one session per user.
    auth_service.start_session(user, get_jti(access_token))

    return jsonify({
        "access_token": access_token
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Logout user and revoke token."""

    jti = get_jwt()["jti"]

    if auth_service.end_session(current_user, jti):
        return jsonify({
            "msg": "Access token has been revoked"
        }), 200

    return jsonify({
        "msg": "Access token has already been revoked"
    }), 200
