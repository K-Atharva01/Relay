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
* Public-key registration
* Public-key lookup
* Encrypted message storage and relay
* Per-user message inbox
* Message retrieval and deletion
* SQLite database
* Basic API testing with shell scripts

---

## Tech Stack

| Component        | Technology                    |
| ---------------- | ----------------------------- |
| Backend          | Python / Flask                |
| Database         | SQLite                        |
| ORM              | SQLAlchemy / Flask-SQLAlchemy |
| Authentication   | JWT                           |
| Password hashing | Werkzeug                      |
| Testing          | Shell scripts, `curl`, `jq`   |

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

---

## API

### Authentication

```http
POST /auth/register
POST /auth/login
POST /auth/logout
```

Registration creates a user account, while login returns a JWT used to authenticate subsequent requests.

---

### Public Keys

```http
POST /keys/addKey
POST /keys/fetchPublicKey
```

Users can register a public key with Relay and retrieve another user's public key when sending a message.

---

### Messages

```http
POST /message/send
GET  /message/inbox
POST /message/getMessageById
POST /message/delete
```

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
