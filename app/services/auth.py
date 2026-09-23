"""Authentication service."""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User


def get_user_by_username(username):
    """Return the user with this username, or None."""
    return User.query.filter_by(username=username).first()


def register_user(name, username, password, phone, email):
    """Register a new user. Returns (user, None) or (None, error message)."""

    # Check whether any unique field is already in use.
    existing = User.query.filter(
        or_(
            User.username == username,
            User.phone == phone,
            User.email == email,
        )
    ).first()

    if existing:
        # Generic message: do not reveal which field is already taken.
        return None, "Username, phone, or email already exists"

    new_user = User(
        name=name,
        username=username,
        phone=phone,
        email=email,
        password_hash=User.set_password(password)
    )

    db.session.add(new_user)

    try:
        db.session.commit()
    except IntegrityError:
        # Protect against a race condition where another request
        # inserts the same unique value between our check and commit.
        db.session.rollback()
        return None, "Username, phone, or email already exists"

    return new_user, None


def authenticate_user(username, password):
    """Return the user if the credentials are valid, otherwise None."""
    user = get_user_by_username(username)

    if not user or not user.check_password(password):
        return None

    return user


def start_session(user, new_jti):
    """Make new_jti the user's only valid token (one session per user).

    Rotating current_jti implicitly invalidates any previous token.
    """
    user.current_jti = new_jti
    db.session.commit()


def end_session(user, jti):
    """Clear the user's session when jti is the current one.

    Returns True when the session was ended, False when jti was not
    the current session (and is therefore already invalid).
    """
    if user.current_jti != jti:
        return False
    user.current_jti = None
    db.session.commit()
    return True
