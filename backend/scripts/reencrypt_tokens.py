"""Re-encrypt stored Meta access tokens after rotating the Fernet key."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from app.database import SessionLocal
from app.models.meta_connection import MetaConnection


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    old_fernet = Fernet(_require_env("OLD_ENCRYPTION_KEY").encode())
    new_fernet = Fernet(_require_env("NEW_ENCRYPTION_KEY").encode())

    db = SessionLocal()
    updated = 0
    skipped = 0
    try:
        for connection in db.query(MetaConnection).all():
            token = connection.encrypted_access_token
            if not token:
                continue
            try:
                plaintext = old_fernet.decrypt(token.encode())
            except InvalidToken:
                skipped += 1
                continue

            connection.encrypted_access_token = new_fernet.encrypt(plaintext).decode()
            updated += 1

        db.commit()
    finally:
        db.close()

    print(f"Re-encrypted {updated} token(s); skipped {skipped} invalid token(s).")


if __name__ == "__main__":
    main()
