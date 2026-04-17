"""
Encryption Utility Module

Provides symmetric encryption/decryption for credentials stored in the database.
Uses Fernet (AES-128-CBC + HMAC-SHA256) with a per-call random IV/salt.
The key is read from the ENCRYPTION_KEY environment variable.
"""

import os
from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    key = os.environ["ENCRYPTION_KEY"]
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plaintext: str) -> str:
    """Encrypts a plaintext password and returns a Fernet token string."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypts a Fernet token and returns the original plaintext password."""
    return _fernet().decrypt(token.encode()).decode()
