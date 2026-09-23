````markdown
# AGENTS.md

## Project Overview

Relay is a Flask REST API for exchanging credentials as public-key-encrypted messages.

The server acts as:

- an authentication service
- a public-key directory
- a ciphertext mailbox
- a message relay

Private keys, key generation, encryption, and decryption are client-side responsibilities. The server must not store private keys or plaintext credentials/messages.

The current stack includes:

- Python
- Flask
- Flask-SQLAlchemy
- SQLite for local development
- flask-jwt-extended
- Flask-Limiter
- cryptography (public-key validation)
- Werkzeug password hashing

The repository currently contains the backend/server component. Do not claim that Relay provides complete end-to-end encryption unless the client-side cryptographic implementation actually exists and implements it correctly.

---

# General Rules

1. Read the existing code before modifying it.
2. Preserve existing functionality unless the task explicitly requires a behavior change.
3. Prefer small, reviewable changes over large rewrites.
4. Do not introduce unnecessary frameworks, services, or abstractions.
5. Do not invent cryptographic protocols or primitives.
6. Use established security libraries for cryptographic operations.
7. Never commit secrets, private keys, tokens, databases, or runtime-generated files.
8. Add or update tests for behavior that changes.
9. Do not claim a security property merely because the documentation describes it.
10. Treat the actual implementation as authoritative for what currently works.

---

# Project Structure

Use a conventional Python/Flask structure:

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
│   │   └── encrypted_message.py
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
├── README.md
├── DESIGN.md
├── AGENTS.md
└── run.py
````

The structure may be simplified when a directory would contain only trivial files.

Do not create abstraction layers merely to make the repository appear more sophisticated.

## Responsibilities

### `app/__init__.py`

Contains:

* application factory
* application initialization
* blueprint registration
* error handlers

Use:

```python
create_app()
```

### `app/config.py`

Contains:

* configuration classes
* environment-backed configuration
* development/test/production configuration where appropriate

### `app/extensions.py`

Contains Flask extension instances such as:

```python
db = SQLAlchemy()
jwt = JWTManager()
```

Extensions should be initialized inside `create_app()`.

### `app/models/`

Contains SQLAlchemy models only.

### `app/routes/`

Contains HTTP/API concerns:

* route definitions
* request parsing
* authentication decorators
* validation
* calling services
* response formatting

Avoid putting substantial business logic directly into routes.

### `app/services/`

Contains business logic and database operations that should not depend directly on Flask request parsing.

Do not create unnecessary service classes.

Simple functions are preferred where appropriate.

### `app/utils/`

Contains genuinely reusable helpers.

### `tests/`

Contains automated tests.

### `scripts/`

Contains developer utilities and API/test helper scripts that are not application code.

### `instance/`

Contains local runtime data such as SQLite databases.

Never commit runtime database files.

---

# Application Factory

Relay should use the Flask application-factory pattern.

Example:

```python
def create_app(config_object=None):
    ...
    return app
```

Do not rely on importing a global Flask application solely to initialize the application.

Initialize extensions separately and attach them through `create_app()`.

Register all blueprints from the application factory.

---

# Virtual Environment

Relay must be developed and tested inside a Python virtual environment.

Use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`.venv/` must never be committed.

All application testing should use the project's virtual environment rather than the system Python installation.

---

# Dependencies

Maintain a `requirements.txt`.

Dependencies should be pinned to known compatible versions.

At minimum, account for the packages actually required by the application, such as:

* Flask
* Flask-SQLAlchemy
* flask-jwt-extended
* Werkzeug
* SQLAlchemy

Do not add dependencies without a clear reason.

When dependencies change:

1. update `requirements.txt`
2. install into a clean virtual environment
3. run the test suite
4. verify application startup
5. run dependency/security checks where appropriate

Use `pip-audit` when appropriate.

---

# Configuration and Secrets

Never hardcode secrets.

Sensitive configuration must come from environment variables or an appropriate secret-management mechanism.

At minimum, configuration should support:

```text
JWT_SECRET_KEY
DATABASE_URL / SQLALCHEMY_DATABASE_URI
FLASK_DEBUG
```

Provide `.env.example` with placeholders only.

Never commit `.env`.

If a secret has previously been committed, treat it as compromised. Rotate it and clean Git history when appropriate.

Do not assume that adding a secret to `.gitignore` removes it from Git history.

---

# JWT Authentication

Relay uses JWT authentication.

Rules:

* Never log access tokens.
* Never expose JWT signing secrets.
* Keep token expiration explicit.
* Preserve JTI-based revocation semantics unless authentication is intentionally redesigned.
* Use the current `token_in_blocklist_loader` mechanism for revocation.
* Do not use deprecated flask-jwt-extended configuration.
* Do not confuse authentication with authorization.

The authenticated user must be resolved consistently before accessing user-owned resources.

If JWT identity contains a username while database relationships use `unique_id`, resolve the username to the corresponding `User` record before querying resources that use `unique_id`.

A user's JWT must never allow access to another user's:

* messages
* keys
* account data
* protected resources

---

# Passwords

Passwords must never be stored in plaintext.

Use Werkzeug's password hashing functions or another established password hashing mechanism.

Never:

* log passwords
* return passwords
* store plaintext passwords
* include real passwords in tests

Validate password input before database operations.

Authentication endpoints should handle malformed input without returning internal 500 errors.

---

# Public Keys

Relay stores public keys. Private keys belong exclusively to clients.

Rules:

* Never accept or store private keys on the server.
* Validate public-key format before storing it.
* Enforce reasonable request-size limits.
* Restrict accepted algorithms/key sizes according to the project's cryptographic design.
* Every public key must have an unambiguous identifier.
* Key ownership must always be verified.
* Users must not be able to modify or delete another user's keys.

Do not assume that a public key returned by Relay is automatically cryptographically authenticated.

The public-key directory and cryptographic identity verification are separate concerns.

If key fingerprints, key pinning, certificates, signatures, or authenticated key rotation are implemented later, follow `DESIGN.md` and use established cryptographic libraries.

---

# Cryptographic Boundary

The intended trust boundary is:

```text
Client
  │
  │ plaintext
  ▼
Client-side encryption
  │
  │ ciphertext
  ▼
Relay
  │
  │ ciphertext storage/routing
  ▼
Recipient
  │
  │ client-side decryption
  ▼
plaintext
```

Relay must not introduce plaintext credential storage.

Relay should not require access to client private keys.

Do not implement custom cryptographic primitives.

Do not describe the server as performing end-to-end encryption unless the complete client-side protocol actually exists.

---

# Messages

Messages stored by Relay should be ciphertext.

Every message operation must enforce ownership.

### Inbox

Only the authenticated recipient can access their inbox.

### Get Message

A user must only be able to retrieve messages belonging to that user.

### Delete Message

A user must only be able to delete their own messages.

Do not rely solely on sequential message IDs for authorization.

Prefer opaque UUID message identifiers when changing the message-ID design.

For production-oriented message handling:

* avoid unbounded inbox responses
* support pagination
* consider message expiration
* consider retention policies
* avoid retaining ciphertext indefinitely when the protocol does not require it

---

# Input Validation

Do not access required request fields before validating the request.

Avoid:

```python
data["username"]
```

before checking the request.

Prefer:

```python
data = request.get_json(silent=True) or {}
username = data.get("username")
```

Validate:

* presence
* type
* length
* format
* allowed values
* request size

Malformed requests must not become unexpected 500 errors.

Use a schema-validation library if validation becomes sufficiently complex to justify one.

---

# Error Handling

Never expose raw exceptions to API clients.

Do not return:

```python
str(e)
```

to users.

Do not expose:

* SQL statements
* database paths
* filesystem paths
* stack traces
* table names
* internal implementation details

Use:

```python
from werkzeug.exceptions import HTTPException
```

HTTP exceptions must preserve their correct status codes.

Unexpected exceptions should:

1. be logged server-side
2. return a generic 500 response

Example:

```python
from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(exc):
    if isinstance(exc, HTTPException):
        return jsonify(
            error=exc.name,
            description=exc.description,
        ), exc.code

    app.logger.exception("Unhandled exception")
    return jsonify(error="Internal Server Error"), 500
```

---

# Database

Use SQLAlchemy models rather than raw SQL in route handlers.

Keep models separate from routes.

Use migrations for intentional schema changes.

Do not commit:

```text
*.db
*.sqlite
*.sqlite3
```

Do not assume SQLite's development concurrency behavior represents production behavior.

Handle expected `IntegrityError` conditions appropriately.

Avoid Python-side counters when uniqueness must be guaranteed under concurrent requests.

Prefer database-generated IDs or UUIDs for globally unique identifiers.

---

# Rate Limiting

Authentication endpoints must not accept unlimited attempts.

Consider rate limiting:

* login
* registration
* password-related endpoints
* expensive endpoints
* abuse-prone endpoints

Use a maintained Flask-compatible rate-limiting library when implementing this functionality.

Document the limits and test expected behavior.

---

# Transport Security

The Flask development server is for local development only.

For network-accessible deployments:

* bind Flask to localhost/private interfaces
* use a proper WSGI server such as Gunicorn
* terminate TLS at a trusted reverse proxy or ingress
* use HTTPS for passwords and bearer tokens
* consider HSTS for HTTPS deployments

Never expose Flask debug mode on a network-accessible server.

---

# Tests

The repository may contain curl/jq API tests. Preserve useful existing tests while introducing a maintainable Python test suite where appropriate.

Tests should cover:

## Authentication

* successful registration
* missing registration fields
* malformed JSON
* duplicate username
* duplicate email
* duplicate phone
* successful login
* invalid login
* logout
* revoked token
* previous token after a new login

## Authorization

* unauthenticated access is rejected
* user cannot access another user's messages
* user cannot delete another user's messages
* user cannot delete another user's keys
* protected resources enforce ownership

## Keys

* key creation
* valid key handling
* invalid key handling
* key lookup
* key ownership
* key deletion
* key rotation when implemented

## Messages

* send
* inbox
* get by ID
* delete
* invalid recipient
* invalid key UID
* concurrent message creation where relevant
* pagination/expiration once implemented

Tests must never use real secrets or production credentials.

Use temporary databases, directories, and generated test data.

---

# Git Hygiene

Never commit:

```text
.env
.venv/
*.token
*.pem
*.key
*.db
*.sqlite
*.sqlite3
instance/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
```

Private keys must never be committed, including test private keys.

Test tokens must be generated at runtime.

Generated databases must not be committed.

If sensitive material was previously committed, rotate it and address Git history separately.

---

# Security-Critical Changes

For changes involving:

* authentication
* JWTs
* authorization
* public keys
* cryptography
* message handling
* secrets
* certificates
* TLS
* database access control

the coding assistant must:

1. Identify the security property being changed.
2. Understand the relevant trust boundary.
3. Make the smallest safe change.
4. Add a regression test where practical.
5. Check for authorization bypasses.
6. Check for information leakage.
7. Avoid custom cryptographic implementations.
8. Follow `DESIGN.md` for cryptographic decisions.

Do not claim that a security issue is fixed without verifying the implementation.

---

# Restructuring Rules

When restructuring the repository:

1. Understand the existing dependency graph first.
2. Move code before redesigning it.
3. Preserve the API contract.
4. Update imports and entry points.
5. Run tests after structural changes.
6. Keep database schema compatibility unless a migration is intentional.
7. Do not rename public API fields merely for consistency.
8. Do not delete functionality because it appears unused.
9. Do not introduce unrelated infrastructure.
10. Keep the refactor easy to review and revert.

A restructuring task must not become an excuse for a complete rewrite.

---

# Documentation

Keep documentation aligned with the implementation.

### `README.md`

Should document:

* project purpose
* architecture
* setup
* virtual environment
* dependencies
* environment variables
* local execution
* testing
* repository structure

### `DESIGN.md`

Should document:

* architecture
* trust boundaries
* authentication model
* message flow
* key-management model
* cryptographic protocol
* security assumptions

Do not silently change `DESIGN.md` to match an implementation that was accidentally changed.

If implementation and design differ, identify the discrepancy explicitly.

---

# Definition of Done

A change is complete only when:

* the application imports successfully
* the intended tests pass
* affected API routes have been tested
* authentication and authorization boundaries remain intact
* no secrets or generated artifacts were added
* error responses do not leak internal exceptions
* documentation is updated when behavior or structure changes
* dependencies are represented correctly in `requirements.txt`
* the application works inside the project's `.venv`
* the resulting code is understandable without relying on historical knowledge of the repository

Do not claim that Relay is secure, production-ready, or fully end-to-end encrypted unless the implementation has actually been verified to provide those properties.

```
```
