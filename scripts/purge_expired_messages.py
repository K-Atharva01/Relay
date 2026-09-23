#!/usr/bin/env python3
"""Delete expired ciphertext for every user.

Expired messages are also purged when a recipient loads their inbox;
this script handles recipients who never return. Run it periodically,
for example daily via cron or Task Scheduler:

    python scripts/purge_expired_messages.py
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import User
from app.services.messages import purge_expired


def main():
    """Purge expired messages for all users and report the total."""
    app = create_app()
    with app.app_context():
        total = sum(purge_expired(user) for user in User.query.all())
    print(f"Purged {total} expired message(s).")


if __name__ == "__main__":
    main()