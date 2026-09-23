# Relay

Relay is a Flask REST API for exchanging credentials and sensitive information as **public-key-encrypted messages**.

The Relay server acts as a trusted communication intermediary for authentication, public-key discovery, ciphertext storage, and message delivery. The sensitive cryptographic operations are intended to happen on the client side, keeping private keys and plaintext credentials outside the Relay server.

> **Current status:** Relay currently implements the backend/server component. The client-side key generation, encryption, and decryption implementation is not yet part of this repository.

---

## Overview

The basic Relay workflow is:

```text
                         Relay Server
                    ┌────────────────────┐
                    │                    │
                    │ Authentication     │
                    │ Public-key lookup  │
                    │ Ciphertext storage │
                    │ Message routing    │
                    │                    │
                    └─────────┬──────────┘
                              │
                 ciphertext only
                              │
             ┌────────────────┴────────────────┐
             │                                 │
          Sender                           Recipient
             │                                 │
       Encrypt locally                    Decrypt locally
````

The intended trust boundary is:

```text
Sender Client
    │
    │ plaintext
    ▼
Client-side encryption
    │
    │ ciphertext
    ▼
Relay Server
    │
    │ store / route ciphertext
    ▼
Recipient Client
    │
    │ client-side decryption
    ▼
plaintext
```

Relay should therefore never need access to a user's private key or plaintext credential.

---

## Features

The current backend provides:

* User registration
* Password hashing
* JWT-based authentication
* JWT revocation
* Public-key registration
* Public-key discovery
* Unique identifiers for registered keys
* Encrypted message submission
* Recipient inbox
* Individual message retrieval
* Message deletion
* User-scoped message authorization
* User-scoped key management

---

## Technology Stack

| Component        | Technology                    |
| ---------------- | ----------------------------- |
| Language         | Python                        |
| Web framework    | Flask                         |
| ORM              | Flask-SQLAlchemy / SQLAlchemy |
| Database         | SQLite                        |
| Authentication   | `flask-jwt-extended`          |
| Password hashing | Werkzeug                      |
| API testing      | `curl` + `jq`                 |
| Environment      | Python virtual environment    |

SQLite is currently intended for local development.

---

## Project Structure

The project follows a conventional Flask application structure:

```text
Relay/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── public_key.py
│   │   ├── encrypted_message.py
│   │   └── revoked_token.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── keys.py
│   │   └── messages.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── keys.py
│   │   └── messages.py
│   └── utils/
│       ├── __init__.py
│       └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
├── migrations/
├── instance/
├── .env.example
├── .gitignore
├── requirements.txt
├── AGENTS.md
├── DESIGN.md
├── README.md
└── run.py
```

### Application

`app/` contains the Flask application.

### Models

`app/models/` contains the database models:

* `User`
* `PublicKey`
* `EncryptedMessage`
* `RevokedToken`

### Routes

`app/routes/` contains the HTTP API endpoints:

* `auth.py` — authentication and account endpoints
* `keys.py` — public-key management
* `messages.py` — encrypted message operations

### Services

`app/services/` contains business logic and database operations that should not be tied directly to HTTP request handling.

### Tests

`tests/` contains automated tests and integration tests.

### Instance

`instance/` contains local runtime data such as the SQLite database.

Runtime data in `instance/` should not be committed to Git.

---

# Installation

## Requirements

You need:

* Python 3
* `pip`
* `venv`
* `git`

Verify Python:

```bash
python3 --version
```

---

## Create a Virtual Environment

Relay should be run and tested inside a Python virtual environment.

From the project directory:

```bash
python3 -m venv .venv
```

Activate it:

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

---

## Install Dependencies

Install the pinned project dependencies:

```bash
pip install -r requirements.txt
```

Verify the environment:

```bash
pip list
```

The virtual environment should be used whenever developing, testing, or running Relay locally.

---

# Configuration

Relay uses environment variables for configuration.

Create a local `.env` based on `.env.example`.

Example:

```env
JWT_SECRET_KEY=replace-with-a-random-secret
DATABASE_URL=sqlite:///instance/relay.db
FLASK_DEBUG=0
```

Never commit `.env`.

Generate a strong JWT signing secret, for example:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The JWT secret must be kept private.

If a secret has previously been committed to Git, changing `.gitignore` is not sufficient. The secret should be considered compromised and rotated.

---

# Running Relay

Activate the virtual environment first:

```bash
source .venv/bin/activate
```

Then start the application using the project's entry point:

```bash
python run.py
```

The exact host and port are controlled by the application's configuration.

For local development, the Flask development server may be used.

Do **not** expose the Flask development server directly to the public internet.

For network-accessible deployments, use a production WSGI server such as Gunicorn behind an appropriate TLS-terminating reverse proxy or ingress.

---

# API Architecture

Relay exposes three primary API areas:

```text
/auth
/keys
/message
```

The high-level flow is:

```text
                    ┌───────────────┐
                    │     Relay     │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
       /auth             /keys            /message
          │                 │                 │
      Accounts        Public keys       Ciphertext
      JWT auth        Key discovery      mailbox
```

---

# Authentication Flow

A user first registers an account.

```text
Client
  │
  │ POST /auth/register
  ▼
Relay
  │
  │ password hashing
  ▼
User database record
```

Passwords are stored as hashes rather than plaintext passwords.

After registration, the user can authenticate:

```text
Client
  │
  │ POST /auth/login
  ▼
Relay
  │
  │ validate credentials
  ▼
JWT
```

The JWT is then supplied as a Bearer token for protected API requests.

Relay also tracks token JTIs for revocation.

Logging in again can invalidate the previous session, and logging out revokes the current token.

---

# Public-Key Flow

A client can register a public key with Relay:

```text
Client
  │
  │ public key
  ▼
Relay
  │
  ├── store public key
  └── assign key identifier
```

The corresponding private key must remain on the client.

When a sender wants to send something to another user:

```text
Sender
   │
   │ request recipient's public key
   ▼
Relay
   │
   │ public key + key_uid
   ▼
Sender
```

The sender can then use the recipient's public key for client-side encryption.

---

# Message Flow

The intended message flow is:

```text
1. Sender authenticates
        │
        ▼
2. Sender obtains recipient public key
        │
        ▼
3. Sender encrypts plaintext locally
        │
        ▼
4. Sender sends ciphertext to Relay
        │
        ▼
5. Relay stores ciphertext
        │
        ▼
6. Recipient requests inbox
        │
        ▼
7. Relay returns ciphertext
        │
        ▼
8. Recipient decrypts locally
```

Relay is therefore intended to handle the **transport and storage of ciphertext**, not plaintext credentials.

---

# Security Model

The intended security model is based on keeping private cryptographic material on the client.

The Relay server may know:

* user accounts
* usernames
* public keys
* key identifiers
* sender/recipient relationships
* timestamps
* ciphertext
* authentication metadata

The Relay server should not possess:

* client private keys
* plaintext credentials
* plaintext messages

A compromise of the Relay database should therefore not directly reveal message plaintext, assuming the client-side cryptographic implementation and key protection are correctly implemented.

> This property depends on the client-side cryptographic protocol. The current repository does not itself implement the complete client-side encryption/decryption system.

---

# Key Trust

Public-key discovery and cryptographic identity verification are separate concerns.

The server returning:

```text
Bob's public key
```

does not by itself prove that the key genuinely belongs to Bob if the server or its database has been compromised.

A future client implementation should address key authenticity through mechanisms such as:

* key fingerprints
* key pinning
* authenticated key rotation
* certificates
* digital signatures

The exact protocol should follow `DESIGN.md`.

Relay should use established cryptographic libraries rather than implementing cryptographic primitives itself.

---

# Authorization

Authentication and authorization are separate.

A valid JWT proves that a request is associated with an authenticated account.

It does **not** automatically grant access to another user's resources.

Message operations must remain scoped to the authenticated recipient.

For example:

```text
Alice JWT
   │
   ├── Alice's messages     ✓
   ├── Alice's keys        ✓
   └── Bob's messages      ✗
```

The same principle applies to public-key management.

---

# Development

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python run.py
```

Before submitting changes:

1. Run the test suite.
2. Verify the application starts.
3. Verify affected API endpoints.
4. Check `git status`.
5. Ensure no secrets or generated files are tracked.

---

# Testing

Relay currently uses API-level tests based on `curl` and `jq`, with Python tests intended for maintainable unit/integration coverage.

Run the available test suite from the activated virtual environment.

Tests should cover at least:

### Authentication

* registration
* login
* invalid credentials
* missing registration fields
* duplicate users
* logout
* token revocation

### Keys

* public-key registration
* public-key lookup
* key ownership
* key deletion
* invalid key input

### Messages

* sending messages
* inbox retrieval
* individual message retrieval
* message deletion
* unauthorized message access
* invalid recipient/key identifiers

Tests must use generated or temporary test data.

Never commit real passwords, JWT tokens, private keys, or production credentials.

---

# Database

SQLite is currently used for local development.

The local database is stored under:

```text
instance/
```

Database files are runtime state and must not be committed.

Database schema changes should be handled through migrations rather than manually modifying production databases.

---

# Production Considerations

The Flask development server is not intended for production deployment.

A network-accessible Relay deployment should use:

```text
Internet
    │
    ▼
TLS / Reverse Proxy
    │
    ▼
WSGI Server
    │
    ▼
Flask Application
    │
    ▼
Database
```

Possible components include:

* Nginx
* Caddy
* Tailscale Serve
* Gunicorn

TLS should terminate before requests reach the Flask application when appropriate.

Debug mode must be disabled.

Secrets must be supplied through environment variables or a dedicated secret-management system.

---

# Current Limitations

The current backend does not yet implement the complete client-side cryptographic protocol.

In particular, the repository does not currently provide the complete:

* client-side key generation
* client-side encryption
* client-side decryption
* identity-key infrastructure
* certificate infrastructure
* signature generation
* signature verification
* authenticated key rotation

These are separate parts of the planned Relay architecture.

---

# Security Issues

Relay is an active development project.

Known areas requiring further hardening include:

* secret management
* production debug configuration
* error handling
* input validation
* authentication rate limiting
* public-key authenticity
* public-key validation
* message ID generation under concurrency
* message expiration and pagination
* revoked-token cleanup
* TLS deployment
* dependency pinning and auditing

These should be addressed systematically rather than assuming the current implementation is production-ready.

---

# Development Philosophy

Relay is intended to remain relatively small and understandable.

Prefer:

```text
simple Flask application
        +
clear trust boundaries
        +
well-defined API
        +
established cryptographic libraries
        +
strong authorization
        +
good tests
```

over unnecessary infrastructure or abstraction.

Do not introduce distributed services or complex infrastructure unless the project's requirements actually justify them.

---

