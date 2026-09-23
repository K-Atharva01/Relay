#!/usr/bin/env python3
"""Interactive Relay API test client.

Run:
    python tests/relay_test_client.py

Provides:
- Automated end-to-end Alice -> Bob flow
- Individual API actions
- Runtime token/key/message state
- Configurable Relay base URL

Uses only Python standard-library modules.
"""

import getpass
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("RELAY_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
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


def api(method, path, body=None, token=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with urlopen(
            Request(BASE_URL + path, data=data, headers=headers, method=method),
            timeout=10,
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
    if not state["tokens"]:
        print("No logged-in users. Login first.")
        return None
    users = list(state["tokens"])
    for i, u in enumerate(users, 1):
        print(f"{i}. {u}")
    try:
        return state["tokens"][users[int(input("Choose user: ")) - 1]]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return None


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
        print(f"Token stored for {username}.")
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


def add_key():
    token = pick_token()
    if not token:
        return False
    username = next(u for u, t in state["tokens"].items() if t == token)
    print("Paste the PEM public key (finish with the -----END PUBLIC KEY----- line):")
    lines = []
    while True:
        line = input()
        lines.append(line)
        if "END PUBLIC KEY" in line:
            break
    key = "\n".join(lines)
    password = getpass.getpass("Account password (required to add a key): ")
    s, d = api("POST", "/keys/addKey", {"public_key": key, "password": password}, token)
    ok = show("ADD PUBLIC KEY", s, d)
    if ok:
        uid = value(d, "key_uid", "keyUid")
        if uid:
            state["keys"][username] = uid
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
    key_uid = state["keys"].get(recipient) or input("Recipient key UID: ").strip()
    ciphertext = input("Ciphertext: ").strip()
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
    return show("GET MESSAGE", s, d)


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
        print("\n--- INDIVIDUAL ACTIONS ---")
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
