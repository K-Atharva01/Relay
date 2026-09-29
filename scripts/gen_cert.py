#!/usr/bin/env python3
"""Generate (or rotate) Relay's self-signed TLS certificate.

run.py creates a certificate automatically on first start; use this to
add hostnames (e.g. your LAN IP) or to rotate it. After rotating, every
client must pin the new certificate.

    python scripts/gen_cert.py --force --hostname 192.168.0.200
"""
import argparse
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tls import (certificate_hostnames, ensure_certificate, fingerprint,
                     generate_certificate)

DEFAULT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "tls")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", action="append", default=[],
                        help="extra DNS name or IP the certificate is valid for "
                             "(repeatable; localhost/127.0.0.1/::1 are always included)")
    parser.add_argument("--cert", default=os.path.join(DEFAULT_DIR, "cert.pem"))
    parser.add_argument("--key", default=os.path.join(DEFAULT_DIR, "key.pem"))
    parser.add_argument("--force", action="store_true",
                        help="replace an existing certificate (clients must re-pin)")
    args = parser.parse_args()

    if args.force:
        cert = generate_certificate(args.cert, args.key, args.hostname)
    else:
        cert = ensure_certificate(args.cert, args.key, args.hostname)

    missing = set(args.hostname) - set(certificate_hostnames(cert))
    if missing:
        print(f"Existing certificate kept; it does not cover {', '.join(sorted(missing))}. "
              "Use --force to replace it.")

    print(f"Certificate: {args.cert}")
    print(f"Valid for:   {', '.join(certificate_hostnames(cert))}")
    print(f"SHA-256:     {fingerprint(cert)}")


if __name__ == "__main__":
    main()
