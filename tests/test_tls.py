"""Tests for HTTPS serving with a self-signed, client-pinned certificate."""

import ssl
import threading
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec

from app import create_app
from app.tls import (build_https_server, certificate_hostnames, check_bind,
                     ensure_certificate, fingerprint, generate_certificate)


def _paths(tmp_path, name='server'):
    return str(tmp_path / f'{name}-cert.pem'), str(tmp_path / f'{name}-key.pem')


class TestCertificate:

    def test_generated_certificate_properties(self, tmp_path):
        cert_path, key_path = _paths(tmp_path)
        cert = generate_certificate(cert_path, key_path, ['192.168.0.200', 'relay.home'])

        assert set(certificate_hostnames(cert)) == {
            'localhost', '127.0.0.1', '::1', '192.168.0.200', 'relay.home'}
        assert isinstance(cert.public_key(), ec.EllipticCurvePublicKey)
        assert cert.public_key().curve.name == 'secp256r1'

        lifetime = cert.not_valid_after_utc - cert.not_valid_before_utc
        assert timedelta(days=729) < lifetime < timedelta(days=731)

        ext = cert.extensions
        assert ext.get_extension_for_class(x509.BasicConstraints).value.ca is False
        assert ext.get_extension_for_class(x509.KeyUsage).value.digital_signature
        assert (x509.oid.ExtendedKeyUsageOID.SERVER_AUTH
                in ext.get_extension_for_class(x509.ExtendedKeyUsage).value)
        ext.get_extension_for_class(x509.SubjectKeyIdentifier)
        ext.get_extension_for_class(x509.AuthorityKeyIdentifier)

    def test_existing_certificate_is_reused(self, tmp_path):
        cert_path, key_path = _paths(tmp_path)
        first = ensure_certificate(cert_path, key_path)
        second = ensure_certificate(cert_path, key_path, ['ignored.example'])
        assert fingerprint(first) == fingerprint(second)

    def test_fingerprint_format(self, tmp_path):
        cert = generate_certificate(*_paths(tmp_path))
        parts = fingerprint(cert).split(':')
        assert len(parts) == 32
        assert all(len(p) == 2 and p == p.upper() for p in parts)


class TestCheckBind:

    @pytest.mark.parametrize('host, tls, debug', [
        ('0.0.0.0', False, False),   # plain HTTP on the network
        ('192.168.0.200', False, False),
        ('0.0.0.0', True, True),     # debugger on the network
    ])
    def test_unsafe_settings_rejected(self, host, tls, debug):
        with pytest.raises(ValueError):
            check_bind(host, tls, debug)

    @pytest.mark.parametrize('host, tls, debug', [
        ('0.0.0.0', True, False),
        ('127.0.0.1', False, False),
        ('localhost', False, True),
        ('::1', True, True),
    ])
    def test_safe_settings_allowed(self, host, tls, debug):
        check_bind(host, tls, debug)


@pytest.fixture
def https_server(tmp_path):
    """A real cheroot HTTPS server on a free port; yields (base_url, cert_path)."""
    cert_path, key_path = _paths(tmp_path)
    generate_certificate(cert_path, key_path)
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key-for-tls-tests-32b',
        'RATELIMIT_ENABLED': False,
    })
    server = build_https_server(app, '127.0.0.1', 0, cert_path, key_path)
    server.prepare()
    thread = threading.Thread(target=server.serve, daemon=True)
    thread.start()
    yield f'https://127.0.0.1:{server.bind_addr[1]}', cert_path
    server.stop()
    thread.join(timeout=5)


def _post(url, body, context):
    request = Request(url, data=body.encode(), method='POST',
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, context=context, timeout=10) as response:
        return response.status, response.read()


class TestHttpsServer:

    def test_pinned_certificate_round_trip(self, https_server):
        base_url, cert_path = https_server
        context = ssl.create_default_context(cafile=cert_path)

        status, _ = _post(f'{base_url}/auth/register', (
            '{"name":"Alice","username":"alice","password":"alicepass1234",'
            '"phone":"100","email":"alice@example.com"}'), context)
        assert status == 201

        status, body = _post(f'{base_url}/auth/login',
                             '{"username":"alice","password":"alicepass1234"}', context)
        assert status == 200
        assert b'access_token' in body

    def test_system_trust_store_rejects_self_signed(self, https_server):
        base_url, _ = https_server
        with pytest.raises(URLError) as exc:
            _post(f'{base_url}/auth/login', '{}', ssl.create_default_context())
        assert isinstance(exc.value.reason, ssl.SSLCertVerificationError)

    def test_different_pinned_certificate_rejected(self, https_server, tmp_path):
        base_url, _ = https_server
        other_cert, _ = _paths(tmp_path, 'other')
        generate_certificate(other_cert, str(tmp_path / 'other-key.pem'))

        with pytest.raises(URLError) as exc:
            _post(f'{base_url}/auth/login', '{}',
                  ssl.create_default_context(cafile=other_cert))
        assert isinstance(exc.value.reason, ssl.SSLCertVerificationError)

    # cheroot drops the plain-HTTP connection, then on garbage collection tries
    # to flush an error reply into the closed socket (WinError 10038). That
    # happens inside cheroot after the test's assertion and is harmless.
    @pytest.mark.filterwarnings('ignore::pytest.PytestUnraisableExceptionWarning')
    def test_plain_http_to_tls_port_fails(self, https_server):
        base_url, cert_path = https_server
        with pytest.raises((URLError, ConnectionError)):
            _post(base_url.replace('https://', 'http://') + '/auth/login', '{}', None)

        # A plain-HTTP probe must not break the server for HTTPS clients.
        with pytest.raises(HTTPError) as exc:
            _post(f'{base_url}/auth/login', '{}',
                  ssl.create_default_context(cafile=cert_path))
        assert exc.value.code == 400

    def test_tls_below_1_3_rejected(self, https_server):
        base_url, cert_path = https_server
        context = ssl.create_default_context(cafile=cert_path)
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        with pytest.raises(URLError):
            _post(f'{base_url}/auth/login', '{}', context)
