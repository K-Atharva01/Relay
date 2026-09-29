"""HTTPS serving with a self-signed, client-pinned certificate.

Relay has no domain or public CA. On first run it generates its own
certificate; clients trust exactly that certificate (they pin it), so no
CA can impersonate the server. TLS 1.3 provides the ECDHE key exchange
and forward secrecy.
"""

import ipaddress
import os
import ssl
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CERT_VALIDITY_DAYS = 730

# Always valid for local access.
DEFAULT_HOSTNAMES = ("localhost", "127.0.0.1", "::1")


def _san_entry(name):
    try:
        return x509.IPAddress(ipaddress.ip_address(name))
    except ValueError:
        return x509.DNSName(name)


def is_loopback(host):
    """True for localhost and loopback IP addresses."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def is_unspecified(host):
    """True for wildcard bind addresses (0.0.0.0, ::), which are not hostnames."""
    try:
        return ipaddress.ip_address(host).is_unspecified
    except ValueError:
        return False


def check_bind(host, tls_enabled, debug):
    """Raise ValueError for unsafe server settings.

    Plain HTTP and the debugger are only allowed on loopback: over a
    network they would expose passwords, tokens, or code execution.
    """
    if debug and not is_loopback(host):
        raise ValueError("Debug mode is only allowed on a loopback address")
    if not tls_enabled and not is_loopback(host):
        raise ValueError("Plain HTTP is only allowed on a loopback address; "
                         "enable TLS to serve on a network")


def generate_certificate(cert_path, key_path, hostnames=()):
    """Create a self-signed EC P-256 certificate and key; return the certificate."""
    names = list(dict.fromkeys([*DEFAULT_HOSTNAMES, *hostnames]))
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Relay")])
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    now = datetime.now(timezone.utc)

    # AKI/SKI and explicit key usages are required by Python's default
    # VERIFY_X509_STRICT checks (Python 3.13+).
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=CERT_VALIDITY_DAYS))
        .add_extension(x509.SubjectAlternativeName([_san_entry(n) for n in names]),
                       critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False,
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                       critical=False)
        .add_extension(ski, critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ski),
                       critical=False)
        .sign(key, hashes.SHA256())
    )

    os.makedirs(os.path.dirname(os.path.abspath(key_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(cert_path)), exist_ok=True)

    # Create the key file owner-only from the start (best effort on Windows).
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key_pem)
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return cert


def ensure_certificate(cert_path, key_path, hostnames=()):
    """Return the existing certificate, generating one if either file is missing."""
    if os.path.exists(cert_path) and os.path.exists(key_path):
        with open(cert_path, "rb") as f:
            return x509.load_pem_x509_certificate(f.read())
    return generate_certificate(cert_path, key_path, hostnames)


def certificate_hostnames(cert):
    """Return the certificate's SAN entries as strings."""
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    return ([str(ip) for ip in san.get_values_for_type(x509.IPAddress)]
            + san.get_values_for_type(x509.DNSName))


def fingerprint(cert):
    """SHA-256 fingerprint of the certificate, as AB:CD:... hex."""
    return ":".join(f"{b:02X}" for b in cert.fingerprint(hashes.SHA256()))


def build_https_server(app, host, port, cert_path, key_path):
    """Return a cheroot WSGI server serving app over TLS 1.3 only."""
    from cheroot import wsgi
    from cheroot.ssl.builtin import BuiltinSSLAdapter

    server = wsgi.Server((host, port), app)
    adapter = BuiltinSSLAdapter(cert_path, key_path)
    # Every client is ours, so there is no need to support older versions.
    adapter.context.minimum_version = ssl.TLSVersion.TLSv1_3
    server.ssl_adapter = adapter
    return server
