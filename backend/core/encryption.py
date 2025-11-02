"""Encryption utilities for sensitive data like Instagram credentials."""
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.fernet import Fernet
from backend.core.config import settings


def get_cipher():
    """Get Fernet cipher instance."""
    if not settings.encryption_key:
        raise ValueError("ENCRYPTION_KEY not configured")
    
    key = settings.encryption_key.encode()
    return Fernet(key)


def encrypt_data(plain_text: str) -> str:
    """Encrypt sensitive data."""
    cipher = get_cipher()
    encrypted = cipher.encrypt(plain_text.encode())
    return urlsafe_b64encode(encrypted).decode()


def decrypt_data(encrypted_text: str) -> str:
    """Decrypt sensitive data."""
    cipher = get_cipher()
    decoded = urlsafe_b64decode(encrypted_text.encode())
    decrypted = cipher.decrypt(decoded)
    return decrypted.decode()
