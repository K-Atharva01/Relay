# Relay

A small personal cybersecurity project exploring **public-key cryptography, authentication, and secure message exchange**.

Relay is a Flask-based backend that allows users to authenticate, register public keys, and exchange encrypted messages without the server needing to handle the plaintext message.

> **Note:** Relay is a learning/personal project and is not intended to be a production-ready secure messaging system. Client-side encryption and decryption are not currently implemented in this repository.

---

## How It Works

```text
┌──────────────┐                         ┌──────────────┐
│   Client A   │                         │   Client B   │
│              │                         │              │
│ Private Key  │                         │ Private Key  │
│ Public Key   │                         │ Public Key   │
└──────┬───────┘                         └──────▲───────┘
       │                                        │
       │ Register Public Key                    │ Fetch Public Key
       │                                        │
       ▼                                        │
┌────────────────────────────────────────────────────┐
│                      Relay                         │
│                    Flask API                       │
│                                                    │
│  Authentication │ Public Keys │ Encrypted Messages │
│                                                    │
│                     SQLite                         │
└────────────────────────────────────────────────────┘
       │
       │ Encrypted Message
       ▼
   Recipient's Inbox
```

The basic flow is:

1. A user creates an account.
2. The user authenticates and receives a JWT.
3. The user's public key is registered with Relay.
4. A sender retrieves the recipient's public key.
5. The sender encrypts a message using the recipient's public key.
6. The encrypted ciphertext is sent to Relay.
7. Relay stores and forwards the ciphertext.
8. The recipient retrieves the ciphertext and decrypts it using their private key.

The server is intended to act as a **relay and key directory**, rather than as a place where plaintext messages are processed.

---

## Features

* User registration and authentication
* JWT-based authentication
* Password hashing using Werkzeug
* Public-key registration with PEM/RSA-2048 validation
* Public-key lookup
* Encrypted message storage and relay
* Per-user message inbox with pagination and expiration
* Message retrieval and deletion
* Rate limiting on registration and login
* Exact-username lookup (no full user directory)
* SQLite database
* API tests with `pytest`, shell scripts, `curl`

---

## Tech Stack

| Component        | Technology                    |
| ---------------- | ----------------------------- |
| Backend          | Python / Flask                |
| Database         | SQLite                        |
| ORM              | SQLAlchemy / Flask-SQLAlchemy |
| Authentication   | JWT                           |
| Password hashing | Werkzeug                      |
| Rate limiting   | Flask-Limiter                 |
| Testing          | `pytest`, shell scripts, `curl` |

---

## Project Structure

```text
Relay/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   ├── config.py
│   ├── extensions.py
│   └── __init__.py
│
├── tests/
├── scripts/
├── instance/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
├── AGENTS.md
└── README.md
```

---

## Running Relay Locally

### 1. Clone the repository

```bash
git clone https://github.com/K-Atharva01/Relay.git
cd Relay
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it:

**Linux/macOS**

```bash
source .venv/bin/activate
```

**Windows**

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

For example:

```env
JWT_SECRET_KEY=change-this-secret
```

Do not commit `.env` or real secrets to Git.

### 5. Start the application

```bash
python run.py
```

The API should then be available locally.

### 6. Run tests and audit dependencies

With the virtual environment active:

```bash
pytest tests/
```

Dependencies in `requirements.txt` are pinned to known-good versions. After changing them, audit for known vulnerabilities:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

---

## API

### Authentication

```http
POST /auth/register
POST /auth/login
POST /auth/logout
```

Registration creates a user account, while login returns a JWT used to authenticate subsequent requests.

Registration validates presence, type, and length before touching the database: `name` ≤ 100, `username` ≤ 50, `phone` ≤ 15, `email` ≤ 100 and `password` ≤ 1024 characters. Missing, non-string, blank, or oversized fields return `400`.

A duplicate `username`, `phone`, or `email` returns `409` with a generic error that does not reveal which field is already taken.

Passwords must be at least 12 characters long.

Sessions: one active token per user. Each login invalidates the previous token, and logout invalidates the current one. Revocation is checked on every protected request by comparing the token's `jti` against the stored current session (`users.current_jti`) — no server-side token list is kept, so nothing grows over time.

### Rate limits

Limits are held in memory (per server process) and keyed by client IP. Behind a reverse proxy, make sure the real client address is forwarded (e.g. Werkzeug `ProxyFix`).

| Endpoint | Limit |
| -------- | ----- |
| `POST /auth/register` | 5 requests per minute per IP |
| `POST /auth/login` | 30 requests per minute per IP, plus 5 failed attempts per minute per username |
| `POST /keys/addKey` | 5 wrong-password attempts per minute per account |

Exceeding a limit returns `429`. Successful logins do not count toward the per-account failure limit; after 5 failed attempts within a minute, further attempts for that username are temporarily rejected. Use a shared store such as Redis when running multiple workers.

---

### Public Keys

```http
POST /keys/addKey
GET  /keys/getAllKeys
POST /keys/fetchPublicKey
POST /keys/deleteKey
```

Public keys must be PEM-encoded (SubjectPublicKeyInfo) **RSA keys of at least 2048 bits**; anything else is rejected with `400`. Individual keys are capped at 16 KB, and all requests are capped at 16 MB (`MAX_CONTENT_LENGTH`). Validation uses the [`cryptography`](https://cryptography.io) library. Note that format validation does not prove a key belongs to its claimed owner — that requires client-side fingerprint verification (see Current Limitations).

Users can register a public key with Relay and retrieve another user's public key when sending a message.

`POST /keys/addKey` takes `public_key` and the account `password`. A valid JWT alone is not enough: a missing password returns `400`, a wrong one returns `403`. This stops someone who has stolen a token from uploading their own key, which `fetchPublicKey` would then give to senders as the newest key.

**Relay does not prove that a key belongs to its user.** Requiring the password does not protect against a malicious or compromised server, or anyone with write access to the database: either can still return a different key. Protecting against that needs a client, which does not exist yet. The client would need to:

* show a fingerprint of each contact's key (for example SHA-256 of the key), computed by the client, for users to compare out of band
* pin each contact's key on first use and warn when it changes
* have users sign a new key with their previous private key, and check that chain before trusting the new key

Relay does not currently notify users when a key is added to their account. `GET /keys/getAllKeys` lists every key with its upload time.

---

### Messages

```http
POST /message/send
GET  /message/sendTo?username=<name>
GET  /message/inbox?limit=50&offset=0
POST /message/getMessageById
POST /message/inbox/deleteMessage
```

`GET /message/sendTo` performs an exact-username lookup. Relay does not expose a full user directory.

`message_uid` is an opaque UUID string assigned when a message is sent. Messages created before this change keep their original numeric identifier and remain retrievable.

The inbox is paginated: `limit` (1–100, default 50) and `offset` (default 0) select a page, and the response is `{"messages": [...], "total": ..., "limit": ..., "offset": ...}`. Invalid values return `400`.

Messages expire. New messages get an `expires_at` timestamp (`MESSAGE_TTL_DAYS`, default 30; `0` disables). Expired messages are excluded from the inbox and by ID, purged when the recipient loads their inbox, and can be purged for every user with `python scripts/purge_expired_messages.py` (run it periodically, e.g. via cron). Rows created before this change have no expiry and are never removed automatically; the `encrypted_messages.expires_at` column is added to existing databases at startup.

Each recipient may store up to `MAX_INBOX_MESSAGES` messages (default 1000). Sending beyond the cap returns `409`.

Messages stored by Relay are intended to be ciphertext.

A simplified message flow looks like:

```text
Sender
  │
  │ Encrypt using recipient's public key
  ▼
Ciphertext
  │
  │ POST /message/send
  ▼
Relay
  │
  │ Stores ciphertext
  ▼
Recipient Inbox
  │
  │ Retrieve ciphertext
  ▼
Recipient
  │
  │ Decrypt using private key
  ▼
Plaintext
```

---

## Security Model

The main idea behind Relay is to keep the **cryptographic boundary on the client**.

Ideally:

```text
Private Key
    │
    └── stays with the user

Public Key
    │
    └── registered with Relay

Plaintext
    │
    └── handled by the client

Ciphertext
    │
    └── stored/forwarded by Relay
```

Relay therefore does not need to know the contents of a message in order to deliver it.

However, the current repository is primarily the **backend portion of this design**. The client-side cryptographic implementation is not currently included.

---

## Current Limitations

Relay is still a work in progress.

Some parts of the larger cryptographic design are not implemented yet, including:

* Client-side key generation
* Actual message encryption/decryption
* Cryptographic message signatures
* Identity-key infrastructure
* Ephemeral session keys
* Certificate/CA infrastructure
* Key rotation
* Strong cryptographic verification of public-key authenticity

The current API demonstrates the backend concepts and message-relay workflow, but should **not be considered a complete end-to-end encrypted messaging system**.

---

## What This Project Explores

Relay was built as a practical way to explore concepts around:

* Public-key cryptography
* Secure credential exchange
* JWT authentication
* Password hashing
* Public-key management
* Encrypted message transport
* Authentication vs. encryption
* Server/client trust boundaries
* API authorization
* Secure application design

---

## Future Improvements

Some planned improvements include:

* Implementing the client-side cryptographic layer
* Improving public-key authenticity and verification
* Adding message signatures
* Supporting key rotation
* Introducing ephemeral session keys
* Improving validation and error handling
* Adding rate limiting
* Adding message expiration
* Improving automated tests

---

## Status

**Personal project / work in progress**

Relay is primarily an experiment and learning project focused on understanding how a backend can support cryptographic message exchange while keeping sensitive plaintext and private keys outside the server.
