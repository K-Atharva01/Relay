"""Public key validation."""

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Maximum accepted public key size in bytes. Real PEM keys are a few KB;
# this blocks oversized blobs well below the global MAX_CONTENT_LENGTH.
MAX_PUBLIC_KEY_BYTES = 16 * 1024

# Minimum accepted RSA modulus size in bits.
MIN_RSA_BITS = 2048


def validate_public_key(pem):
    """Return an error message if this PEM public key is unacceptable, else None.

    Accepted keys are PEM-encoded (SubjectPublicKeyInfo) RSA public keys
    of at least MIN_RSA_BITS bits.
    """
    if len(pem.encode("utf-8")) > MAX_PUBLIC_KEY_BYTES:
        return f"Public key is too large (maximum {MAX_PUBLIC_KEY_BYTES} bytes)"

    try:
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
    except UnsupportedAlgorithm:
        return "Public key uses an unsupported algorithm"
    except ValueError:
        return "Public key must be a valid PEM-encoded public key"

    if not isinstance(key, rsa.RSAPublicKey):
        return "Public key must be an RSA public key"

    if key.key_size < MIN_RSA_BITS:
        return f"RSA public key must be at least {MIN_RSA_BITS} bits"

    return None