"""
Password Encryption Migration Script

Encrypts any plain-text passwords currently stored in the credentials table.
Safe to run multiple times — already-encrypted Fernet tokens are left untouched.

Usage:
    python3 migrate_encrypt_passwords.py
"""

import os
import mysql.connector
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()


def _fernet() -> Fernet:
    key = os.environ["ENCRYPTION_KEY"]
    return Fernet(key.encode() if isinstance(key, str) else key)


def is_already_encrypted(fernet: Fernet, value: str) -> bool:
    try:
        fernet.decrypt(value.encode())
        return True
    except (InvalidToken, Exception):
        return False


def main():
    fernet = _fernet()

    conn = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"]
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT site, customer_id, password FROM credentials")
    rows = cursor.fetchall()

    updated = 0
    skipped = 0
    for row in rows:
        if is_already_encrypted(fernet, row["password"]):
            skipped += 1
            continue

        encrypted = fernet.encrypt(row["password"].encode()).decode()
        update_cursor = conn.cursor()
        update_cursor.execute(
            "UPDATE credentials SET password=%s WHERE site=%s AND customer_id=%s",
            (encrypted, row["site"], row["customer_id"])
        )
        update_cursor.close()
        updated += 1
        print(f"  Encrypted: {row['site']} (customer {row['customer_id']})")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\nDone. {updated} password(s) encrypted, {skipped} already encrypted.")


if __name__ == "__main__":
    main()
