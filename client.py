#!/usr/bin/env python3
"""Interactive Relay API test client.

Run:
    python client.py

Provides:
- Automated end-to-end Alice -> Bob flow
- Individual API actions
- Runtime token/key/message state
- Configurable Relay base URL

HTTPS connections trust only the server's pinned certificate
(RELAY_CA_FILE, default instance/tls/cert.pem), never the system CAs.
Plain http:// is allowed only for loopback addresses.

"Add public key" can generate an RSA key pair; the private key is saved
outside the repository in RELAY_KEY_DIR (default ~/.relay/keys).

"Send message" can encrypt a typed message to the recipient's latest
public key (JWE, RSA-OAEP-256 + AES-256-GCM) before sending, and "Get
message" can decrypt it with the matching local private key. This is
encryption only: messages are not signed, so the recipient cannot verify
who sent them beyond what the server reports.

Uses Python standard-library modules, plus the project's `cryptography`
and `jwcrypto` dependencies for keys and encryption.
"""

import getpass
import ipaddress
import json
import os
import ssl
import sys
import uuid
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = os.environ.get("RELAY_BASE_URL", "https://127.0.0.1:5000").rstrip("/")
CA_FILE = os.environ.get("RELAY_CA_FILE", os.path.join(ROOT, "instance", "tls", "cert.pem"))
# Server-side cap on a stored message (app/routes/messages.py).
MAX_MESSAGE_CHARS = 5000
# Generated key pairs are kept outside the repository so private keys are never committed.
KEY_DIR = os.environ.get("RELAY_KEY_DIR", os.path.join(os.path.expanduser("~"), ".relay", "keys"))
state = {"tokens": {}, "keys": {}, "messages": {}}

# A valid RSA-2048 public key for automated tests. Public keys are not
# secret; no private key is stored in the repository.
TEST_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0fyhhOMqWCTRFbs8K3wh
eglhMWZ8lgmL3PsrwVjCAaNED6ahxIjXJZUiHO1wHCIdFwnhd6SZwDP5q71fx997
1iw8mnlnPRmdvEW/zjI1TURHoxpxah6gpe3M/Hv8Vaw05zPSvUj2QF4MgErmDAnq
lC93XAvPiP2H2ft7ddfYVfPWLGXJ7VoegqYY1DCpCF0DQYDXVpRgm23zkfKNqHZd
CKLoZS6kC52zUQkhEl4z2Osep9IH50t3PdpfOpZz8ZGFI/w53iBKPNGLcDRfxsqo
P0Ofh6WMBQ1pixHft9Nz1A5YhhZ2bsl500OBnoJgQWm5He/gvK28mFWRY8zvwOVK
5QIDAQAB
-----END PUBLIC KEY-----"""


def parse(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _is_loopback(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_base_url(url):
    """Return an error message if url is not safe to send credentials to, else None."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return None
    if parts.scheme == "http" and _is_loopback(parts.hostname or ""):
        return None
    return "Use https:// (plain http:// is only allowed for loopback addresses)"


def tls_context():
    """SSL context that trusts only the pinned server certificate."""
    return ssl.create_default_context(cafile=CA_FILE)


def api(method, path, body=None, token=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    error = check_base_url(BASE_URL)
    if error:
        print(f"[CONFIG ERROR] {error}")
        return None, None
    context = None
    if BASE_URL.startswith("https://"):
        try:
            context = tls_context()
        except (FileNotFoundError, ssl.SSLError) as e:
            print(f"[TLS ERROR] cannot load pinned certificate {CA_FILE}: {e}")
            return None, None

    try:
        with urlopen(
            Request(BASE_URL + path, data=data, headers=headers, method=method),
            timeout=10,
            context=context,
        ) as r:
            return r.status, parse(r.read().decode(errors="replace"))
    except HTTPError as e:
        return e.code, parse(e.read().decode(errors="replace"))
    except URLError as e:
        print(f"[CONNECTION ERROR] {e.reason}")
        return None, None


def show(label, status, data, expected=None):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)
    if status is None:
        return False
    print(f"HTTP {status}")
    print(json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data)
    ok = expected is None and 200 <= status < 300 or expected and status in expected
    print("[PASS]" if ok else "[FAIL]")
    return ok


def pick_token():
    """Return the token to act as.

    With one logged-in user, use it without asking. With several, ask,
    defaulting (Enter) to the user acted as last time.
    """
    if not state["tokens"]:
        print("No logged-in users. Login first.")
        return None
    users = list(state["tokens"])
    current = state.get("current") if state.get("current") in users else users[-1]
    if len(users) > 1:
        for i, u in enumerate(users, 1):
            print(f"{i}. {u}{' (current)' if u == current else ''}")
        raw = input(f"Act as [{current}]: ").strip()
        if raw:
            try:
                current = users[int(raw) - 1]
            except (ValueError, IndexError):
                print("Invalid selection.")
                return None
    state["current"] = current
    print(f"Acting as {current}.")
    return state["tokens"][current]


def pick_stored(label, options):
    """Choose from stored options by number, or type a value manually.

    options: list of (display_name, value) pairs.
    Returns the chosen value, or None if nothing was entered.
    """
    for i, (name, _) in enumerate(options, 1):
        print(f"{i}. {name}")
    hint = "number or value" if options else "value"
    raw = input(f"{label} ({hint}): ").strip()
    if not raw:
        return None
    if options and raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1][1]
    return raw


def value(data, *names):
    if isinstance(data, dict):
        for name in names:
            if name in data:
                return data[name]
        for v in data.values():
            x = value(v, *names)
            if x is not None:
                return x
    return None


def register():
    payload = {
        "name": input("Name: ").strip(),
        "username": input("Username: ").strip(),
        "phone": input("Phone: ").strip(),
        "email": input("Email: ").strip(),
        "password": getpass.getpass("Password: "),
    }
    s, d = api("POST", "/auth/register", payload)
    return show("REGISTER", s, d)


def login():
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    s, d = api("POST", "/auth/login", {
        "username": username, "password": password
    })
    ok = show("LOGIN", s, d)
    token = value(d, "access_token", "token", "jwt")
    if ok and token:
        state["tokens"][username] = token
        state["current"] = username
        print(f"Token stored for {username}; now acting as {username}.")
    return ok


def logout():
    token = pick_token()
    if not token:
        return False
    s, d = api("POST", "/auth/logout", token=token)
    ok = show("LOGOUT", s, d)
    if ok:
        for u, t in list(state["tokens"].items()):
            if t == token:
                del state["tokens"][u]
    return ok


def _key_index_path():
    return os.path.join(KEY_DIR, "index.json")


def load_key_index():
    """Return {key_uid: private key path} for keys generated by this client."""
    try:
        with open(_key_index_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def remember_private_key(key_uid, private_path):
    """Record which local private key file belongs to an uploaded key_uid."""
    index = load_key_index()
    index[key_uid] = private_path
    os.makedirs(KEY_DIR, exist_ok=True)
    with open(_key_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def generate_key_pair(username):
    """Generate an RSA key pair; save both halves under KEY_DIR.

    Returns (public PEM string, private key path), or (None, None).

    The private key never leaves this machine and is stored outside the
    repository (owner-only file, optionally passphrase-encrypted).
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("[ERROR] Key generation needs the 'cryptography' package "
              "(pip install -r requirements.txt).")
        return None, None

    bits_raw = input("Key size in bits (2048/3072/4096) [3072]: ").strip() or "3072"
    if bits_raw not in ("2048", "3072", "4096"):
        print("Invalid key size.")
        return None, None
    passphrase = getpass.getpass("Passphrase to encrypt the private key (Enter for none): ")
    if passphrase and getpass.getpass("Repeat passphrase: ") != passphrase:
        print("Passphrases do not match.")
        return None, None

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=int(bits_raw))
    encryption = (serialization.BestAvailableEncryption(passphrase.encode())
                  if passphrase else serialization.NoEncryption())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption)
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    os.makedirs(KEY_DIR, exist_ok=True)
    # Random suffix: two keys generated within the same second must not collide.
    stem = os.path.join(
        KEY_DIR, f"{username}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}")
    fd = os.open(f"{stem}-private.pem", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(private_pem)
    with open(f"{stem}-public.pem", "wb") as f:
        f.write(public_pem)

    print(f"Private key: {stem}-private.pem"
          + ("" if passphrase else "  (NOT encrypted; keep it safe)"))
    print(f"Public key:  {stem}-public.pem")
    return public_pem.decode(), f"{stem}-private.pem"


def _jwcrypto():
    """Import jwcrypto lazily so the rest of the client works without it."""
    try:
        from jwcrypto import jwe, jwk
        return jwe, jwk
    except ImportError:
        print("[ERROR] Encryption needs the 'jwcrypto' package "
              "(pip install -r requirements.txt).")
        return None, None


def encrypt_message(plaintext, public_pem, key_uid):
    """Encrypt plaintext to a recipient's RSA public key as a compact JWE.

    Standard JOSE hybrid encryption: a random AES-256-GCM key encrypts the
    message, and RSA-OAEP-256 encrypts that key. kid names the key used.
    """
    jwe, jwk = _jwcrypto()
    if not jwe:
        return None
    token = jwe.JWE(
        plaintext.encode("utf-8"),
        protected=json.dumps({"alg": "RSA-OAEP-256", "enc": "A256GCM", "kid": key_uid}),
    )
    token.add_recipient(jwk.JWK.from_pem(public_pem.encode()))
    return token.serialize(compact=True)


def looks_like_jwe(message):
    """Compact JWE: five base64url parts separated by dots."""
    return isinstance(message, str) and message.count(".") == 4


def decrypt_message(compact, private_path):
    """Decrypt a compact JWE with a local private key file; return the plaintext."""
    jwe, jwk = _jwcrypto()
    if not jwe:
        return None
    with open(private_path, "rb") as f:
        pem = f.read()
    password = None
    if b"ENCRYPTED" in pem:
        password = getpass.getpass("Private key passphrase: ").encode()
    key = jwk.JWK.from_pem(pem, password=password)
    token = jwe.JWE()
    token.deserialize(compact, key=key)
    return token.payload.decode("utf-8")


def read_key_file(path):
    """Return the contents of a PEM file, or None if it cannot be read."""
    if not path:
        print("No path given.")
        return None
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, UnicodeDecodeError) as e:
        print(f"[ERROR] Cannot read {path}: {e}")
        return None


def paste_key():
    """Read a pasted PEM block, ending at its -----END ...----- line."""
    print("Paste the PEM public key (finish with the -----END PUBLIC KEY----- line):")
    lines = []
    while True:
        line = input()
        lines.append(line)
        if line.strip().startswith("-----END "):
            return "\n".join(lines)


def add_key():
    token = pick_token()
    if not token:
        return False
    username = next(u for u, t in state["tokens"].items() if t == token)

    print("1. Generate a new RSA key pair")
    print("2. Load a public key from a file")
    print("3. Paste a public key")
    choice = input("Choose [1]: ").strip() or "1"
    private_path = None
    if choice == "1":
        key, private_path = generate_key_pair(username)
    elif choice == "2":
        key = read_key_file(input("Path to PEM public key file: ").strip().strip('"'))
    elif choice == "3":
        key = paste_key()
    else:
        print("Invalid choice.")
        return False
    if not key:
        return False
    if "PRIVATE KEY" in key:
        # Never send a private key to the server, even though it would reject it.
        print("[REFUSED] That is a PRIVATE key. Only the public key may be uploaded.")
        return False

    password = getpass.getpass("Account password (required to add a key): ")
    s, d = api("POST", "/keys/addKey", {"public_key": key, "password": password}, token)
    ok = show("ADD PUBLIC KEY", s, d)
    if ok:
        uid = value(d, "key_uid", "keyUid")
        if uid:
            state["keys"][username] = uid
            if private_path:
                # Lets "Get message" find the right private key to decrypt with.
                remember_private_key(uid, private_path)
    return ok


def fetch_key():
    token = pick_token()
    if not token:
        return False
    username = input("Recipient username: ").strip()
    s, d = api("POST", "/keys/fetchPublicKey", {"username": username}, token)
    ok = show("FETCH PUBLIC KEY", s, d)
    if ok:
        uid = value(d, "key_uid", "keyUid")
        if uid:
            state["keys"][username] = uid
    return ok


def delete_key():
    token = pick_token()
    if not token:
        return False
    options = [(f"{u}: {uid}", uid) for u, uid in state["keys"].items()]
    uid = pick_stored("Key UID", options)
    if not uid:
        print("No key UID given.")
        return False
    s, d = api("POST", "/keys/deleteKey", {"key_uid": uid}, token)
    ok = show("DELETE PUBLIC KEY", s, d)
    if ok:
        for u, stored in list(state["keys"].items()):
            if stored == uid:
                del state["keys"][u]
    return ok


def list_keys():
    token = pick_token()
    if not token:
        return False
    username = next(u for u, t in state["tokens"].items() if t == token)
    s, d = api("GET", "/keys/getAllKeys", token=token)
    ok = show("ALL PUBLIC KEYS", s, d)
    if ok and isinstance(d, dict):
        keys = d.get("public_keys") or []
        if keys:
            # Server returns newest first; remember it for delete/send.
            latest = value(keys[0], "key_uid")
            if latest:
                state["keys"][username] = latest
    return ok


def check_user():
    token = pick_token()
    if not token:
        return False
    username = input("Username to look up: ").strip()
    if not username:
        print("No username given.")
        return False
    s, d = api("GET", f"/message/sendTo?username={quote(username)}", token=token)
    return show("USER LOOKUP", s, d)


def send_message():
    token = pick_token()
    if not token:
        return False
    recipient = input("Recipient username: ").strip()
    if not recipient:
        print("No recipient given.")
        return False

    # Always encrypt to the recipient's newest key, fetched fresh: a cached
    # key_uid may belong to a key they have since replaced or deleted.
    s, d = api("POST", "/keys/fetchPublicKey", {"username": recipient}, token)
    if s != 200 or not isinstance(d, dict):
        return show("FETCH RECIPIENT KEY", s, d)
    key_uid, public_pem = d["key_uid"], d["public_key"]
    state["keys"][recipient] = key_uid
    print(f"Using {recipient}'s latest public key: {key_uid}")

    print("1. Type a message (encrypted here, before it is sent)")
    print("2. Send ciphertext you already have")
    choice = input("Choose [1]: ").strip() or "1"
    if choice == "1":
        plaintext = input("Message: ")
        if not plaintext.strip():
            print("Message is empty.")
            return False
        ciphertext = encrypt_message(plaintext, public_pem, key_uid)
        if not ciphertext:
            return False
        if len(ciphertext) > MAX_MESSAGE_CHARS:
            print(f"[ERROR] Encrypted message is {len(ciphertext)} characters; "
                  f"the server accepts at most {MAX_MESSAGE_CHARS}. Shorten the message.")
            return False
        print(f"Encrypted ({len(ciphertext)} chars): {ciphertext[:60]}...")
    elif choice == "2":
        ciphertext = input("Ciphertext: ").strip()
    else:
        print("Invalid choice.")
        return False

    s, d = api("POST", "/message/send", {
        "recipient": recipient,
        "message": ciphertext,
        "key_uid": key_uid,
    }, token)
    ok = show("SEND MESSAGE", s, d)
    if ok:
        uid = value(d, "message_uid", "messageUid", "id")
        if uid is not None:
            state["messages"][str(uid)] = d
    return ok


def inbox():
    token = pick_token()
    if not token:
        return False
    s, d = api("GET", "/message/inbox", token=token)
    ok = show("INBOX", s, d)
    if ok:
        items = d if isinstance(d, list) else (d.get("messages") or []) if isinstance(d, dict) else []
        for item in items:
            uid = value(item, "message_uid", "messageUid", "id")
            if uid is not None:
                state["messages"][str(uid)] = item
    return ok


def _pick_message(label):
    options = [(uid, uid) for uid in state["messages"]]
    return pick_stored(label, options)


def get_message():
    token = pick_token()
    if not token:
        return False
    uid = _pick_message("Message UID")
    if not uid:
        print("No message UID given.")
        return False
    s, d = api("POST", "/message/getMessageById", {"message_uid": uid}, token)
    ok = show("GET MESSAGE", s, d)
    if ok and isinstance(d, dict) and looks_like_jwe(d.get("message")):
        if input("Decrypt it with your private key? [Y/n]: ").strip().lower() in ("", "y", "yes"):
            decrypt_and_show(d["message"], d.get("key_uid"))
    return ok


def decrypt_and_show(compact, key_uid):
    """Find the private key for key_uid (or ask for one) and print the plaintext."""
    private_path = load_key_index().get(key_uid)
    if private_path and os.path.exists(private_path):
        print(f"Using private key {private_path}")
    else:
        private_path = input(f"Path to the private key for {key_uid}: ").strip().strip('"')
        private_path = os.path.expanduser(private_path)
    try:
        plaintext = decrypt_message(compact, private_path)
    except OSError as e:
        print(f"[ERROR] Cannot read private key: {e}")
        return
    except Exception as e:
        # Wrong key, wrong passphrase, or tampered ciphertext all end up here.
        print(f"[ERROR] Decryption failed ({type(e).__name__}): wrong key/passphrase "
              "or the message was altered.")
        return
    if plaintext is not None:
        print("-" * 70)
        print(f"Decrypted message:\n{plaintext}")
        print("-" * 70)


def delete_message():
    token = pick_token()
    if not token:
        return False
    uid = _pick_message("Message UID")
    if not uid:
        print("No message UID given.")
        return False
    s, d = api("POST", "/message/inbox/deleteMessage", {"message_uid": uid}, token)
    ok = show("DELETE MESSAGE", s, d)
    if ok:
        state["messages"].pop(uid, None)
    return ok


def automated():
    suffix = uuid.uuid4().hex[:8]
    alice = {
        "name": "Relay Test Alice", "username": f"alice_{suffix}",
        "phone": f"91{suffix}", "email": f"alice_{suffix}@example.com",
        "password": "RelayTestPassword123!"
    }
    bob = {
        "name": "Relay Test Bob", "username": f"bob_{suffix}",
        "phone": f"92{suffix}", "email": f"bob_{suffix}@example.com",
        "password": "RelayTestPassword123!"
    }

    print(f"\nAlice: {alice['username']}\nBob:   {bob['username']}")
    results = []

    def step(label, method, path, body=None, token=None, expected=None):
        s, d = api(method, path, body, token)
        ok = show(label, s, d, expected)
        results.append(ok)
        return d if ok else {}

    step("1. REGISTER ALICE", "POST", "/auth/register", alice, expected={200, 201})
    step("2. REGISTER BOB", "POST", "/auth/register", bob, expected={200, 201})

    d = step("3. LOGIN ALICE", "POST", "/auth/login",
             {"username": alice["username"], "password": alice["password"]},
             expected={200})
    at = value(d, "access_token", "token", "jwt")

    d = step("4. LOGIN BOB", "POST", "/auth/login",
             {"username": bob["username"], "password": bob["password"]},
             expected={200})
    bt = value(d, "access_token", "token", "jwt")

    if not at or not bt:
        print("\n[STOP] Could not obtain both JWTs.")
        return

    ak = step("5. ADD ALICE KEY", "POST", "/keys/addKey",
              {"public_key": TEST_PUBLIC_KEY_PEM,
               "password": alice["password"]}, at,
              {200, 201})
    bk = step("6. ADD BOB KEY", "POST", "/keys/addKey",
              {"public_key": TEST_PUBLIC_KEY_PEM,
               "password": bob["password"]}, bt,
              {200, 201})

    bob_uid = value(bk, "key_uid", "keyUid")

    # A JWT alone must not be enough to replace Bob's key (key substitution).
    # Only one wrong password is sent: addKey allows 5 per minute per account.
    step("7. ADD BOB KEY WITHOUT PASSWORD (expect 400)", "POST", "/keys/addKey",
         {"public_key": "ATTACKER_PUBLIC_KEY"}, bt, {400})
    step("8. ADD BOB KEY WITH WRONG PASSWORD (expect 403)", "POST", "/keys/addKey",
         {"public_key": "ATTACKER_PUBLIC_KEY",
          "password": "NotBobsPassword123!"}, bt, {403})

    fetched = step("9. ALICE FETCHES BOB KEY", "POST", "/keys/fetchPublicKey",
                   {"username": bob["username"]}, at, {200})

    print("\n" + "=" * 70)
    print("10. FETCHED KEY IS BOB'S ORIGINAL KEY")
    print("=" * 70)
    unchanged = (value(fetched, "key_uid", "keyUid") == bob_uid
                 and value(fetched, "public_key") == TEST_PUBLIC_KEY_PEM)
    print("[PASS]" if unchanged else "[FAIL] Bob's key was replaced or not returned.")
    results.append(unchanged)

    bob_uid = value(fetched, "key_uid", "keyUid") or bob_uid

    msg = f"RELAY_AUTOMATED_TEST_CIPHERTEXT_{suffix}"
    sent = step("11. ALICE SENDS MESSAGE", "POST", "/message/send", {
        "recipient": bob["username"],
        "message": msg,
        "key_uid": bob_uid,
    }, at, {200, 201})

    message_uid = value(sent, "message_uid", "messageUid", "id")

    inbox_data = step("12. BOB CHECKS INBOX", "GET", "/message/inbox",
                      token=bt, expected={200})

    if message_uid is None and isinstance(inbox_data, dict):
        for k in ("messages", "inbox", "data"):
            items = inbox_data.get(k)
            if isinstance(items, list) and items:
                message_uid = value(items[0], "message_uid", "messageUid", "id")
                break

    if message_uid is not None:
        step("13. BOB GETS MESSAGE", "POST", "/message/getMessageById",
             {"message_uid": message_uid}, bt, {200})
        step("14. BOB DELETES MESSAGE", "POST", "/message/inbox/deleteMessage",
             {"message_uid": message_uid}, bt, {200, 204})
    else:
        print("[SKIP] Could not determine message UID.")

    step("15. BOB LOGS OUT", "POST", "/auth/logout", token=bt, expected={200, 204})

    passed = sum(results)
    print("\n" + "#" * 70)
    print(f"AUTOMATED FLOW: {passed}/{len(results)} steps passed")
    print("#" * 70)


ACTIONS = {
    "1": ("Register", register),
    "2": ("Login", login),
    "3": ("Logout", logout),
    "4": ("Add public key", add_key),
    "5": ("Fetch public key", fetch_key),
    "6": ("Delete public key", delete_key),
    "7": ("List my public keys", list_keys),
    "8": ("Send message", send_message),
    "9": ("View inbox", inbox),
    "10": ("Get message", get_message),
    "11": ("Delete message", delete_message),
    "12": ("Look up user by username", check_user),
}


def individual():
    while True:
        acting = state.get("current") if state.get("current") in state["tokens"] else None
        print(f"\n--- INDIVIDUAL ACTIONS (acting as: {acting or 'nobody, login first'}) ---")
        for n, (name, _) in ACTIONS.items():
            print(f"{n}. {name}")
        print("0. Back")
        choice = input("Choose: ").strip()
        if choice == "0":
            return
        if choice in ACTIONS:
            try:
                ACTIONS[choice][1]()
            except Exception as e:
                print(f"[ERROR] {type(e).__name__}: {e}")
        else:
            print("Invalid choice.")


def main():
    global BASE_URL
    print("=" * 70)
    print("RELAY API TEST CLIENT")
    print(f"Base URL: {BASE_URL}")
    print(f"Pinned certificate: {CA_FILE}")
    print("=" * 70)

    while True:
        print("\n1. Automated end-to-end flow")
        print("2. Individual actions")
        print("3. Change base URL")
        print("4. Show stored state")
        print("0. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            automated()
        elif choice == "2":
            individual()
        elif choice == "3":
            BASE_URL = input(f"Base URL [{BASE_URL}]: ").strip() or BASE_URL
            BASE_URL = BASE_URL.rstrip("/")
        elif choice == "4":
            print(json.dumps({
                "base_url": BASE_URL,
                "logged_in_users": list(state["tokens"]),
                "acting_as": state.get("current"),
                "key_uids": state["keys"],
                "message_uids": list(state["messages"]),
            }, indent=2))
        elif choice == "0":
            return
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
