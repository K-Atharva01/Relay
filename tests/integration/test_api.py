"""Integration tests for the Relay API."""

import os
import sys
import json
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'PROPAGATE_EXCEPTIONS': True
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
            'password': 'testpass123',
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
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        
        # Try to register duplicate
        response = client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        assert response.status_code == 409

    def test_login(self, client):
        """Test user login."""
        # Register user first
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'test@example.com'
        })
        
        # Login
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123'
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


class TestKeys:
    """Test key management endpoints."""

    def test_upload_key(self, client):
        """Test uploading a public key."""
        # Register and login
        client.post('/auth/register', json={
            'name': 'Test User',
            'username': 'keyuser',
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'key@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'keyuser',
            'password': 'testpass123'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Upload key
        response = client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {token}'},
            json={'public_key': '-----BEGIN PUBLIC KEY-----\ntest-key\n-----END PUBLIC KEY-----'}
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
            'password': 'testpass123',
            'phone': '1234567891',
            'email': 'key2@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'keyuser2',
            'password': 'testpass123'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Upload a key first
        client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {token}'},
            json={'public_key': '-----BEGIN PUBLIC KEY-----\ntest-key\n-----END PUBLIC KEY-----'}
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
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'sender@example.com'
        })
        sender_login = client.post('/auth/login', json={
            'username': 'sender',
            'password': 'testpass123'
        })
        sender_token = json.loads(sender_login.data)['access_token']
        
        # Register and login recipient
        client.post('/auth/register', json={
            'name': 'Recipient User',
            'username': 'recipient',
            'password': 'testpass123',
            'phone': '1234567891',
            'email': 'recipient@example.com'
        })
        recipient_login = client.post('/auth/login', json={
            'username': 'recipient',
            'password': 'testpass123'
        })
        recipient_token = json.loads(recipient_login.data)['access_token']
        
        # Upload key for recipient
        key_response = client.post('/keys/addKey',
            headers={'Authorization': f'Bearer {recipient_token}'},
            json={'public_key': '-----BEGIN PUBLIC KEY-----\ntest-key\n-----END PUBLIC KEY-----'}
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
            'password': 'testpass123',
            'phone': '1234567890',
            'email': 'inbox@example.com'
        })
        login_response = client.post('/auth/login', json={
            'username': 'inboxuser',
            'password': 'testpass123'
        })
        token = json.loads(login_response.data)['access_token']
        
        # Get inbox
        response = client.get('/message/inbox',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
