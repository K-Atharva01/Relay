#!/usr/bin/env python3
"""Run the Relay server.

Serves HTTPS by default with a self-signed certificate that is generated
on first run (instance/tls/). Clients pin that certificate; compare the
printed fingerprint with the one a client shows when trusting it.

Usage:
    python run.py

Environment variables (also read from .env):
    JWT_SECRET_KEY: Secret key for JWT signing (required)
    DATABASE_URL: Database connection string (default: sqlite:///secure_exchange.db)
    FLASK_ENV: 'production', 'testing' or 'development' (default)
    FLASK_DEBUG: '1' for the debugger and reloader, loopback only (default: 0)
    HOST: Bind address (default: 127.0.0.1; 0.0.0.0 to serve on a network)
    PORT: Port (default: 5000)
    TLS_ENABLED: '0' to serve plain HTTP, loopback only (default: 1)
    TLS_CERT_FILE / TLS_KEY_FILE: Certificate and key (default: instance/tls/cert.pem, key.pem)
    TLS_EXTRA_HOSTNAMES: Comma-separated extra names/IPs for a new certificate,
        e.g. your LAN IP (default: none)
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env before importing the app: app/config.py reads os.environ at import.
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.tls import (build_https_server, certificate_hostnames, check_bind,
                     ensure_certificate, fingerprint, is_unspecified)


def main():
    """Run the Relay server."""
    app = create_app()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    tls_enabled = os.environ.get("TLS_ENABLED", "1") == "1"

    try:
        check_bind(host, tls_enabled, debug)
    except ValueError as e:
        sys.exit(f"Refusing to start: {e}")

    tls_dir = os.path.join(app.instance_path, "tls")
    cert_file = os.environ.get("TLS_CERT_FILE") or os.path.join(tls_dir, "cert.pem")
    key_file = os.environ.get("TLS_KEY_FILE") or os.path.join(tls_dir, "key.pem")

    if tls_enabled:
        hostnames = [name.strip()
                     for name in os.environ.get("TLS_EXTRA_HOSTNAMES", "").split(",")
                     if name.strip()]
        if not is_unspecified(host):
            hostnames.append(host)

        cert = ensure_certificate(cert_file, key_file, hostnames)
        missing = set(hostnames) - set(certificate_hostnames(cert))
        if missing:
            print(f"WARNING: certificate does not cover {', '.join(sorted(missing))}. "
                  f"Regenerate it with: python scripts/gen_cert.py --force "
                  + " ".join(f"--hostname {name}" for name in sorted(missing)))

        print(f"Certificate: {cert_file}")
        print(f"Valid for:   {', '.join(certificate_hostnames(cert))}")
        print(f"SHA-256:     {fingerprint(cert)}")

    scheme = "https" if tls_enabled else "http"
    # flush: the fingerprint must reach logs (e.g. under Docker) before serving.
    print(f"Starting Relay on {scheme}://{host}:{port} (debug: {debug})", flush=True)

    if debug:
        # Werkzeug development server: reloader and debugger, loopback only.
        ssl_context = (cert_file, key_file) if tls_enabled else None
        app.run(host=host, port=port, debug=True, ssl_context=ssl_context)
        return

    if tls_enabled:
        server = build_https_server(app, host, port, cert_file, key_file)
    else:
        from cheroot import wsgi
        server = wsgi.Server((host, port), app)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
