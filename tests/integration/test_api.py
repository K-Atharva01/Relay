"""Integration tests for the Relay API."""

import os
import sys
import json
import pytest
from functools import lru_cache

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app import create_app


@lru_cache(maxsize=1)
def sample_public_key_pem():
    """A valid RSA-2048 public key, generated at runtime (never committed)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'PROPAGATE_EXCEPTIONS': True,
        'RATELIMIT_ENABLED': False,
    })
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestAuth:
    """Test authentication endpoints."""

    def test_register_user(self, client):
        """Test user registration."""
        response = client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'User registered successfully'

    def test_register_duplicate_user(self, client):
        """Test duplicate user registration."""
        # Register first user
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        
        # Try to register duplicate
        response = client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        assert response.status_code == 409

    @pytest.mark.parametrize('overrides', [
        {'username': 'otheruser'},                       # same phone + email
        {'phone': '0987654321'},                        # same username + email
        {'email': 'other@example.com'},                 # same username + phone
    ])
    def test_register_partial_duplicate_is_rejected(self, client, overrides):
        """Reusing only one unique field must be caught (OR semantics, not AND)."""
        base = {
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        }
        client.post('/auth/register', json=base)

        payload = {**base, **overrides}
        response = client.post('/auth/register', json=payload)
        assert response.status_code == 409

    @pytest.mark.parametrize('overrides', [
        {'username': 'otheruser'},
        {'phone': '0987654321'},
        {'email': 'other@example.com'},
    ])
    def test_duplicate_error_is_generic(self, client, overrides):
        """The 409 body must not reveal which field is already taken."""
        base = {
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        }
        client.post('/auth/register', json=base)

        response = client.post('/auth/register', json={**base, **overrides})
        assert response.status_code == 409
        error = response.get_json()['error']
        assert error == 'Username, phone, or email already exists'
        assert 'SQL' not in error and 'UNIQUE' not in error

    def test_login(self, client):
        """Test user login."""
        # Register user first
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        
        # Login
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpass1234'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpass'
        })
        assert response.status_code == 401

    def test_register_missing_fields(self, client):
        """Missing fields must return 400, not 500."""
        response = client.post('/auth/register', json={})
        assert response.status_code == 400

        response = client.post('/auth/register', json={'username': 'onlyuser'})
        assert response.status_code == 400

    def test_register_blank_field(self, client):
        """Whitespace-only fields must be rejected."""
        response = client.post('/auth/register', json={
            'name': '   ', 'username': 'testuser', 'password': 'testpass1234',
            'phone': '1234567890', 'email': 'test@example.com'
        })
        assert response.status_code == 400

    @pytest.mark.parametrize('field,value', [
        ('name', 'N' * 101),
        ('username', 'u' * 51),
        ('password', 'p' * 1025),
        ('phone', '1' * 16),
        ('email', 'e' * 101),
    ])
    def test_register_field_too_long(self, client, field, value):
        """Oversized fields must return 400 before reaching the database."""
        payload = {
            'name': 'Test User', 'username': 'testuser', 'password': 'testpass1234',
            'phone': '1234567890', 'email': 'test@example.com'
        }
        payload[field] = value
        response = client.post('/auth/register', json=payload)
        assert response.status_code == 400
        assert 'at most' in response.get_json()['error']


class TestKeys:
    """Test key management endpoints."""

    def test_upload_key(self, client):
        """Test uploading a public key."""
        # Register and login
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'keyuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'key@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'keyuser',
            'password': 'testpass1234'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Upload key
        response = client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {token}'},
            json={'public_key': sample_public_key_pem(),
                  'password': 'testpass1234'}
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'key_uid' in data

    def test_get_keys(self, client):
        """Test getting user's keys."""
        # Register and login
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'keyuser2',
            'password': 'testpass1234',
            'phone': '1234567891',
            'email': 'key2@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'keyuser2',
            'password': 'testpass1234'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Upload a key first
        client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {token}'},
            json={'public_key': sample_public_key_pem(),
                  'password': 'testpass1234'}
        )
        
        # Get keys
        response = client.get('/keys/getAllKeys',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'public_keys' in data
        assert len(data['public_keys']) == 1


class TestMessages:
    """Test message endpoints."""

    def test_send_message(self, client):
        """Test sending a message."""
        # Register and login sender
        client.post('/auth/register', json={
            'name': 'Sender User',
            'username': 'sender',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'sender@example.com'
        })
        sender_login = client.post('/auth/login', json={
            'username': 'sender',
            'password': 'testpass1234'
        })
        sender_token = json.loads(sender_login.data)['access_token']
        
        # Register and login recipient
        client.post('/auth/register', json={
            'name': 'Recipient User',
            'username': 'recipient',
            'password': 'testpass1234',
            'phone': '1234567891',
            'email': 'recipient@example.com'
        })
        recipient_login = client.post('/auth/login', json={
            'username': 'recipient',
            'password': 'testpass1234'
        })
        recipient_token = json.loads(recipient_login.data)['access_token']
        
        # Upload key for recipient
        key_response = client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {recipient_token}'},
            json={'public_key': sample_public_key_pem(),
                  'password': 'testpass1234'}
        )
        key_uid = json.loads(key_response.data)['key_uid']
        
        # Send message
        response = client.post('/message/send',
            headers={'Authorization': f'Bearer {sender_token}'},
            json={
                'recipient': 'recipient',
                'message': 'Encrypted message content',
                'key_uid': key_uid
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message_uid' in data

    def test_get_inbox(self, client):
        """Test getting inbox."""
        # Register and login user
        client.post('/auth/register', json={
            'name': 'Inbox User',
            'username': 'inboxuser',
            'password': 'testpass1234',
            'phone': '1234567890',
            'email': 'inbox@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'inboxuser',
            'password': 'testpass1234'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Get inbox
        response = client.get('/message/inbox',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data['messages'], list)
        assert data['total'] == 0
        assert data['limit'] == 50
        assert data['offset'] == 0


def register_and_login(client, username, phone):
    client.post('/auth/register', json={
        'name': username,
        'username': username,
        'password': 'testpass1234',
        'phone': phone,
        'email': f'{username}@example.com'
    })
    response = client.post('/auth/login', json={
        'username': username,
        'password': 'testpass1234'
    })
    return {'Authorization': f"Bearer {response.get_json()['access_token']}"}


def add_key(client, headers):
    response = client.post('/keys/addKey', headers=headers, json={
        'public_key': sample_public_key_pem(),
        'password': 'testpass1234'
    })
    return response.get_json()['key_uid']


class TestSessions:
    """Test login/logout token handling."""

    def test_login_after_logout(self, client):
        """Logging in again after logging out must not fail (was a 500)."""
        headers = register_and_login(client, 'alice', '100')
        assert client.post('/auth/logout', headers=headers).status_code == 200

        response = client.post('/auth/login', json={
            'username': 'alice',
            'password': 'testpass1234'
        })
        assert response.status_code == 200

    def test_logged_out_token_is_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')
        client.post('/auth/logout', headers=headers)

        assert client.get('/keys/getAllKeys', headers=headers).status_code == 401

    def test_previous_token_rejected_after_new_login(self, client):
        old_headers = register_and_login(client, 'alice', '100')
        client.post('/auth/login', json={'username': 'alice', 'password': 'testpass1234'})

        assert client.get('/keys/getAllKeys', headers=old_headers).status_code == 401

    def test_only_latest_session_token_is_valid(self, client):
        """Every login rotates current_jti: all earlier tokens die."""
        first_headers = register_and_login(client, 'alice', '100')

        tokens = []
        for _ in range(3):
            response = client.post('/auth/login', json={
                'username': 'alice', 'password': 'testpass1234'
            })
            assert response.status_code == 200
            tokens.append(response.get_json()['access_token'])

        # Every earlier session is rejected...
        assert client.get('/keys/getAllKeys',
                          headers=first_headers).status_code == 401
        for stale in tokens[:-1]:
            headers = {'Authorization': f'Bearer {stale}'}
            assert client.get('/keys/getAllKeys',
                              headers=headers).status_code == 401

        # ...while the latest one still works.
        latest = {'Authorization': f'Bearer {tokens[-1]}'}
        assert client.get('/keys/getAllKeys', headers=latest).status_code == 200


class TestMalformedInput:
    """Malformed request bodies must return 400, not 500."""

    @pytest.mark.parametrize('path', [
        '/auth/register',
        '/auth/login',
        '/keys/addKey',
        '/keys/fetchPublicKey',
        '/keys/deleteKey',
        '/message/send',
        '/message/getMessageById',
        '/message/inbox/deleteMessage',
    ])
    @pytest.mark.parametrize('body', ['[1, 2]', '"text"', 'not json'])
    def test_non_object_body(self, client, path, body):
        headers = register_and_login(client, 'alice', '100')
        response = client.post(path, headers=headers, data=body, content_type='application/json')
        assert response.status_code == 400

    def test_register_non_string_password(self, client):
        response = client.post('/auth/register', json={
            'name': 'A', 'username': 'alice', 'password': 12345,
            'phone': '100', 'email': 'a@example.com'
        })
        assert response.status_code == 400

    def test_send_non_string_message(self, client):
        sender = register_and_login(client, 'alice', '100')
        recipient = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, recipient)

        response = client.post('/message/send', headers=sender, json={
            'recipient': 'bob', 'message': ['x'], 'key_uid': key_uid
        })
        assert response.status_code == 400


class TestOwnership:
    """Users can only act on their own keys and messages."""

    def test_cannot_delete_another_users_key(self, client):
        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        bob_key = add_key(client, bob)

        response = client.post('/keys/deleteKey', headers=alice, json={'key_uid': bob_key})
        assert response.status_code == 404

        response = client.post('/keys/deleteKey', headers=bob, json={'key_uid': bob_key})
        assert response.status_code == 200

    def test_message_round_trip_and_ownership(self, client):
        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, bob)

        sent = client.post('/message/send', headers=alice, json={
            'recipient': 'bob', 'message': 'ciphertext', 'key_uid': key_uid
        })
        message_uid = sent.get_json()['message_uid']

        # Alice cannot read or delete Bob's message.
        assert client.post('/message/getMessageById', headers=alice,
                           json={'message_uid': message_uid}).status_code == 404
        assert client.post('/message/inbox/deleteMessage', headers=alice,
                           json={'message_uid': message_uid}).status_code == 404

        inbox = client.get('/message/inbox', headers=bob).get_json()
        assert [m['sender'] for m in inbox['messages']] == ['alice']
        assert inbox['total'] == 1

        response = client.post('/message/getMessageById', headers=bob,
                               json={'message_uid': message_uid})
        assert response.status_code == 200
        assert response.get_json()['message'] == 'ciphertext'

        assert client.post('/message/inbox/deleteMessage', headers=bob,
                           json={'message_uid': message_uid}).status_code == 200
        assert client.get('/message/inbox', headers=bob).get_json()['messages'] == []


class TestMessageUID:
    """message_uid must be an opaque, collision-free identifier."""

    def test_send_returns_distinct_uuid_message_uids(self, client):
        import uuid as uuid_mod

        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, bob)

        uids = []
        for i in range(3):
            response = client.post('/message/send', headers=alice, json={
                'recipient': 'bob', 'message': f'ciphertext-{i}',
                'key_uid': key_uid
            })
            assert response.status_code == 200
            uid = response.get_json()['message_uid']
            assert isinstance(uid, str)
            uuid_mod.UUID(uid)  # parses as a UUID: opaque, not a counter
            uids.append(uid)

        # Independent generation: no shared counter that could collide.
        assert len(set(uids)) == 3

        # Every uid is independently retrievable by the recipient.
        for i, uid in enumerate(uids):
            response = client.post('/message/getMessageById', headers=bob,
                                   json={'message_uid': uid})
            assert response.status_code == 200
            assert response.get_json()['message'] == f'ciphertext-{i}'

    def test_legacy_integer_message_uids_still_accepted(self, client):
        """Rows created before the UUID change use integer-like uids."""
        from app.extensions import db
        from app.models import EncryptedMessage, User

        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')

        alice_user = User.query.filter_by(username='alice').first()
        bob_user = User.query.filter_by(username='bob').first()
        db.session.add(EncryptedMessage(
            message_uid='1',
            sender_id=alice_user.unique_id,
            recipient_id=bob_user.unique_id,
            encrypted_message='legacy-ciphertext',
            key_uid='legacy-key',
        ))
        db.session.commit()

        # Integer bodies (as returned by the old /send) still resolve.
        response = client.post('/message/getMessageById', headers=bob,
                               json={'message_uid': 1})
        assert response.status_code == 200
        assert response.get_json()['message'] == 'legacy-ciphertext'


class TestKeyValidation:
    """addKey must only store well-formed RSA public keys of adequate size."""

    def _add(self, client, headers, pem):
        return client.post('/keys/addKey', headers=headers, json={
            'public_key': pem, 'password': 'testpass1234'
        })

    def test_non_pem_key_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = self._add(client, headers, 'ALICE_FAKE_KEY')
        assert response.status_code == 400
        assert 'PEM' in response.get_json()['error']

    def test_pem_envelope_with_garbage_body_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = self._add(
            client, headers,
            '-----BEGIN PUBLIC KEY-----\ntest-key\n-----END PUBLIC KEY-----')
        assert response.status_code == 400
        assert 'PEM' in response.get_json()['error']

    def test_weak_rsa_key_rejected(self, client):
        from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

        weak = rsa_mod.generate_private_key(public_exponent=65537, key_size=1024)
        pem = weak.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        headers = register_and_login(client, 'alice', '100')
        response = self._add(client, headers, pem)
        assert response.status_code == 400
        assert '2048' in response.get_json()['error']

    def test_non_rsa_key_rejected(self, client):
        from cryptography.hazmat.primitives.asymmetric import ec

        ec_key = ec.generate_private_key(ec.SECP256R1())
        pem = ec_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        headers = register_and_login(client, 'alice', '100')
        response = self._add(client, headers, pem)
        assert response.status_code == 400
        assert 'RSA' in response.get_json()['error']

    def test_oversized_key_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = self._add(client, headers, 'A' * (17 * 1024))
        assert response.status_code == 400
        assert 'too large' in response.get_json()['error']

    def test_valid_rsa_2048_accepted(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = self._add(client, headers, sample_public_key_pem())
        assert response.status_code == 201

    def test_request_over_content_length_cap_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = client.post('/keys/addKey', headers=headers, json={
            'public_key': 'A' * (17 * 1024 * 1024),
            'password': 'testpass1234',
        })
        assert response.status_code == 413


@pytest.fixture
def small_inbox_client():
    """Client whose recipients can store at most 2 messages."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'PROPAGATE_EXCEPTIONS': True,
        'RATELIMIT_ENABLED': False,
        'MAX_INBOX_MESSAGES': 2,
    })
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestInboxRetention:
    """Inbox pagination, message expiry, and the per-recipient cap."""

    def test_inbox_pagination(self, client):
        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, bob)

        uids = []
        for i in range(5):
            response = client.post('/message/send', headers=alice, json={
                'recipient': 'bob', 'message': f'ciphertext-{i}',
                'key_uid': key_uid
            })
            assert response.status_code == 200
            uids.append(response.get_json()['message_uid'])

        page1 = client.get('/message/inbox?limit=2&offset=0',
                           headers=bob).get_json()
        assert page1['total'] == 5
        assert page1['limit'] == 2
        assert page1['offset'] == 0
        assert len(page1['messages']) == 2

        page2 = client.get('/message/inbox?limit=2&offset=3',
                           headers=bob).get_json()
        assert page2['total'] == 5
        assert len(page2['messages']) == 2

        # Newest first, and pages do not overlap.
        seen1 = [m['message_uid'] for m in page1['messages']]
        seen2 = [m['message_uid'] for m in page2['messages']]
        assert seen1 == [uids[4], uids[3]]
        assert seen2 == [uids[1], uids[0]]
        assert not set(seen1) & set(seen2)

    @pytest.mark.parametrize('query', [
        'limit=0', 'limit=101', 'limit=abc', 'limit=-1',
        'offset=-1', 'offset=x',
    ])
    def test_invalid_pagination_rejected(self, client, query):
        headers = register_and_login(client, 'alice', '100')
        response = client.get(f'/message/inbox?{query}', headers=headers)
        assert response.status_code == 400

    def test_expired_message_is_hidden_and_purged(self, client):
        from datetime import datetime

        from app.extensions import db
        from app.models import EncryptedMessage, User

        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, bob)

        sent = client.post('/message/send', headers=alice, json={
            'recipient': 'bob', 'message': 'ciphertext', 'key_uid': key_uid
        }).get_json()
        uid = sent['message_uid']

        # New messages get an expiry by default (MESSAGE_TTL_DAYS=30).
        row = EncryptedMessage.query.filter_by(message_uid=uid).first()
        assert row.expires_at is not None

        # Expire it explicitly.
        row.expires_at = datetime(2000, 1, 1)
        db.session.commit()

        # Expired messages are not retrievable by id or shown in the inbox.
        assert client.post('/message/getMessageById', headers=bob,
                           json={'message_uid': uid}).status_code == 404
        inbox = client.get('/message/inbox', headers=bob).get_json()
        assert inbox['messages'] == []
        assert inbox['total'] == 0

        # Loading the inbox purged the row and freed the counter.
        assert EncryptedMessage.query.filter_by(message_uid=uid).first() is None
        user = User.query.filter_by(username='bob').first()
        assert user.current_messages == 0

    def test_inbox_full_returns_409_and_expiry_frees_space(self,
                                                           small_inbox_client):
        from datetime import datetime

        from app.extensions import db
        from app.models import EncryptedMessage

        client = small_inbox_client
        alice = register_and_login(client, 'alice', '100')
        bob = register_and_login(client, 'bob', '200')
        key_uid = add_key(client, bob)

        for i in range(2):
            response = client.post('/message/send', headers=alice, json={
                'recipient': 'bob', 'message': f'ciphertext-{i}',
                'key_uid': key_uid
            })
            assert response.status_code == 200

        # Cap (MAX_INBOX_MESSAGES=2) reached.
        response = client.post('/message/send', headers=alice, json={
            'recipient': 'bob', 'message': 'overflow', 'key_uid': key_uid
        })
        assert response.status_code == 409
        assert 'inbox is full' in response.get_json()['error']

        # Expire both stored messages; the next send purges and succeeds.
        for row in EncryptedMessage.query.all():
            row.expires_at = datetime(2000, 1, 1)
        db.session.commit()

        response = client.post('/message/send', headers=alice, json={
            'recipient': 'bob', 'message': 'after-purge', 'key_uid': key_uid
        })
        assert response.status_code == 200


class TestSendToLookup:
    """sendTo must be an exact-username lookup, not a user directory."""

    def test_requires_auth(self, client):
        assert client.get('/message/sendTo?username=bob').status_code == 401

    def test_requires_username(self, client):
        headers = register_and_login(client, 'alice', '100')
        assert client.get('/message/sendTo', headers=headers).status_code == 400

    def test_unknown_user_returns_404(self, client):
        headers = register_and_login(client, 'alice', '100')
        response = client.get('/message/sendTo?username=nobody', headers=headers)
        assert response.status_code == 404

    def test_exact_lookup_does_not_leak_directory(self, client):
        register_and_login(client, 'alice', '100')
        register_and_login(client, 'bob', '200')
        headers = register_and_login(client, 'carol', '300')

        response = client.get('/message/sendTo?username=bob', headers=headers)
        assert response.status_code == 200
        assert response.get_json() == {'username': 'bob'}


class TestPasswordPolicy:
    """Registration enforces a minimum password length of 12."""

    def test_short_password_rejected(self, client):
        response = client.post('/auth/register', json={
            'name': 'Test User', 'username': 'testuser', 'password': 'short',
            'phone': '1234567890', 'email': 'test@example.com'
        })
        assert response.status_code == 400
        assert 'at least 12' in response.get_json()['error']

    def test_minimum_length_accepted(self, client):
        response = client.post('/auth/register', json={
            'name': 'Test User', 'username': 'testuser',
            'password': 'testpass1234',  # exactly 12 characters
            'phone': '1234567890', 'email': 'test@example.com'
        })
        assert response.status_code == 201


@pytest.fixture
def limited_client():
    """Test client with rate limiting enabled (normal tests disable it)."""
    from app.extensions import limiter

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'PROPAGATE_EXCEPTIONS': True,
        'RATELIMIT_ENABLED': True,
    })
    limiter.reset()
    with app.test_client() as client:
        yield client
    limiter.reset()


class TestRateLimiting:
    """Registration and login must not accept unlimited attempts."""

    def test_login_locked_out_after_repeated_failures(self, limited_client):
        register_and_login(limited_client, 'victim', '111')

        failed = {'username': 'victim', 'password': 'WrongPassword1!'}
        statuses = [
            limited_client.post('/auth/login', json=failed).status_code
            for _ in range(6)
        ]
        assert statuses[:5] == [401] * 5
        assert statuses[5] == 429

    def test_successful_logins_do_not_count_toward_lockout(self, limited_client):
        register_and_login(limited_client, 'victim', '111')

        good = {'username': 'victim', 'password': 'testpass1234'}
        for _ in range(6):
            response = limited_client.post('/auth/login', json=good)
            assert response.status_code == 200

    def test_registration_rate_limited_per_ip(self, limited_client):
        for i in range(5):
            response = limited_client.post('/auth/register', json={
                'name': 'RL', 'username': f'rl{i}',
                'password': 'testpass1234',
                'phone': str(900 + i), 'email': f'rl{i}@example.com'
            })
            assert response.status_code == 201

        response = limited_client.post('/auth/register', json={
            'name': 'RL', 'username': 'rl5',
            'password': 'testpass1234',
            'phone': '905', 'email': 'rl5@example.com'
        })
        assert response.status_code == 429

    def test_add_key_locked_out_after_wrong_passwords(self, limited_client):
        """A stolen JWT must not allow unlimited password guesses via addKey."""
        headers = register_and_login(limited_client, 'victim', '111')

        wrong = {'public_key': 'PUBLIC_KEY', 'password': 'WrongPassword1!'}
        statuses = [
            limited_client.post('/keys/addKey', headers=headers, json=wrong).status_code
            for _ in range(6)
        ]
        assert statuses[:5] == [403] * 5
        assert statuses[5] == 429

    def test_add_key_limit_is_per_account(self, limited_client):
        victim = register_and_login(limited_client, 'victim', '111')
        other = register_and_login(limited_client, 'other', '222')

        wrong = {'public_key': sample_public_key_pem(),
                 'password': 'WrongPassword1!'}
        for _ in range(5):
            limited_client.post('/keys/addKey', headers=victim, json=wrong)

        response = limited_client.post('/keys/addKey', headers=other, json={
            'public_key': sample_public_key_pem(), 'password': 'testpass1234'
        })
        assert response.status_code == 201


class TestKeySubstitution:
    """Adding a key (which changes what senders encrypt to) needs the password, not just a JWT."""

    def test_add_key_without_password_is_rejected(self, client):
        headers = register_and_login(client, 'alice', '100')

        response = client.post('/keys/addKey', headers=headers, json={'public_key': 'PUBLIC_KEY'})
        assert response.status_code == 400
        assert client.get('/keys/getAllKeys', headers=headers).get_json()['public_keys'] == []

    @pytest.mark.parametrize('password', ['WrongPassword1!', 12345])
    def test_add_key_with_wrong_password_is_rejected(self, client, password):
        headers = register_and_login(client, 'alice', '100')

        response = client.post('/keys/addKey', headers=headers, json={
            'public_key': 'PUBLIC_KEY', 'password': password
        })
        assert response.status_code in (400, 403)
        assert client.get('/keys/getAllKeys', headers=headers).get_json()['public_keys'] == []

    def test_stolen_token_cannot_replace_fetched_key(self, client):
        bob = register_and_login(client, 'bob', '200')
        alice = register_and_login(client, 'alice', '100')
        original_uid = add_key(client, bob)

        # Someone holding Bob's token but not his password tries to upload their own key.
        response = client.post('/keys/addKey', headers=bob, json={
            'public_key': 'ATTACKER_KEY', 'password': 'WrongPassword1!'
        })
        assert response.status_code == 403

        fetched = client.post('/keys/fetchPublicKey', headers=alice, json={'username': 'bob'})
        assert fetched.get_json()['key_uid'] == original_uid


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
