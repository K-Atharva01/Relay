"""Tests for the in-place schema migration of encrypted_messages.expires_at."""

from sqlalchemy import create_engine, inspect, text

from app import _migrate_schema

LEGACY_SCHEMA = """
CREATE TABLE encrypted_messages (
    id INTEGER PRIMARY KEY,
    message_uid VARCHAR(100) NOT NULL,
    sender_id VARCHAR(36) NOT NULL,
    recipient_id VARCHAR(36) NOT NULL,
    encrypted_message TEXT NOT NULL,
    key_uid VARCHAR(100) NOT NULL,
    timestamp DATETIME
)
"""


def _columns(engine):
    return {c["name"] for c in inspect(engine).get_columns("encrypted_messages")}


def test_expires_at_added_to_legacy_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text(LEGACY_SCHEMA))
    assert "expires_at" not in _columns(engine)

    _migrate_schema(engine)
    assert "expires_at" in _columns(engine)


def test_migration_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text(LEGACY_SCHEMA))

    _migrate_schema(engine)
    _migrate_schema(engine)  # second run must be a no-op
    assert "expires_at" in _columns(engine)


def test_migration_skips_missing_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    _migrate_schema(engine)  # no error when the table does not exist yet


def test_revoked_tokens_table_dropped(tmp_path):
    """Revocation moved to User.current_jti; the old table is removed."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text(LEGACY_SCHEMA))
        connection.execute(text(
            "CREATE TABLE revoked_tokens ("
            "id INTEGER PRIMARY KEY, "
            "jti VARCHAR(120) NOT NULL UNIQUE, "
            "created_at DATETIME)"
        ))

    _migrate_schema(engine)
    assert not inspect(engine).has_table("revoked_tokens")
    assert "expires_at" in _columns(engine)

    _migrate_schema(engine)  # idempotent
    assert not inspect(engine).has_table("revoked_tokens")