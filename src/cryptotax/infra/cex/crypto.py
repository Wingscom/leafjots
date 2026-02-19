"""Fernet encryption/decryption for CEX API credentials."""

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(key: str) -> bytes:
    """Derive a valid 32-byte Fernet key from an arbitrary string."""
    raw = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_value(plaintext: str, key: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    f = Fernet(_derive_key(key))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str, key: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    f = Fernet(_derive_key(key))
    return f.decrypt(ciphertext.encode()).decode()
