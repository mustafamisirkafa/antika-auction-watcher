"""
Credential Encryption Module

Provides Fernet-based symmetric encryption for sensitive credentials
(API keys, passwords, tokens) before storing in database or Redis.

Usage:
    from backend.core.encryption import encrypt_credential, decrypt_credential
    
    encrypted = encrypt_credential("my-secret-api-key")
    # Store encrypted in DB
    
    original = decrypt_credential(encrypted)
    # Use original for API calls

Environment:
    MASTER_KEY: Base64-encoded Fernet key (required)
                Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Security:
    - Master key must be rotated periodically (recommendation: every 90 days)
    - Old keys should be kept for decryption during migration
    - Keys must never be committed to version control
    - Use environment variables or secret management systems
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail"""
    pass


class CredentialEncryptor:
    """
    Handles encryption and decryption of sensitive credentials.
    
    Supports key rotation by maintaining a list of valid keys
    (current + legacy keys for decryption-only).
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryptor with master key.
        
        Args:
            master_key: Base64-encoded Fernet key. If None, reads from MASTER_KEY env var.
        
        Raises:
            EncryptionError: If master key is missing or invalid
        """
        self.master_key = master_key or os.getenv("MASTER_KEY")
        
        if not self.master_key:
            raise EncryptionError(
                "MASTER_KEY environment variable not set. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        try:
            self.cipher = Fernet(self.master_key.encode() if isinstance(self.master_key, str) else self.master_key)
        except Exception as e:
            raise EncryptionError(f"Invalid MASTER_KEY format: {e}")
        
        # Support for legacy keys (for decryption during rotation)
        self.legacy_keys = self._load_legacy_keys()
        if self.legacy_keys:
            all_ciphers = [self.cipher] + [Fernet(k.encode()) for k in self.legacy_keys]
            self.multi_cipher = Fernet(all_ciphers[0]._encryption_key)  # Primary for encryption
            self.legacy_ciphers = all_ciphers[1:]  # Legacy for decryption fallback
        else:
            self.multi_cipher = self.cipher
            self.legacy_ciphers = []
    
    def _load_legacy_keys(self) -> list[str]:
        """
        Load legacy encryption keys from environment.
        
        Expected format: LEGACY_KEYS=key1,key2,key3
        
        Returns:
            List of legacy key strings
        """
        legacy = os.getenv("LEGACY_KEYS", "")
        if not legacy:
            return []
        return [k.strip() for k in legacy.split(",") if k.strip()]
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext credential.
        
        Args:
            plaintext: The credential to encrypt
        
        Returns:
            Base64-encoded encrypted string
        
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.multi_cipher.encrypt(plaintext.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted credential.
        
        Attempts decryption with current key, then falls back to legacy keys.
        
        Args:
            ciphertext: Base64-encoded encrypted string
        
        Returns:
            Original plaintext credential
        
        Raises:
            EncryptionError: If decryption fails with all available keys
        """
        if not ciphertext:
            return ""
        
        # Try current key first
        try:
            decrypted_bytes = self.multi_cipher.decrypt(ciphertext.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            # Fallback to legacy keys
            for legacy_cipher in self.legacy_ciphers:
                try:
                    decrypted_bytes = legacy_cipher.decrypt(ciphertext.encode("utf-8"))
                    return decrypted_bytes.decode("utf-8")
                except InvalidToken:
                    continue
            
            # All keys failed
            raise EncryptionError("Decryption failed: invalid token or corrupted data")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")
    
    def rotate_key(self, new_master_key: str, re_encrypt_data: callable):
        """
        Rotate the master encryption key.
        
        Process:
        1. Set new key as primary
        2. Add old key to legacy keys
        3. Re-encrypt all existing credentials with new key
        
        Args:
            new_master_key: New Fernet key (base64-encoded)
            re_encrypt_data: Callback function that receives (old_cipher, new_cipher)
                            and re-encrypts all stored credentials
        
        Example:
            def migrate_credentials(old_cipher, new_cipher):
                all_users = db.query(User).all()
                for user in all_users:
                    if user.encrypted_api_key:
                        decrypted = old_cipher.decrypt(user.encrypted_api_key)
                        user.encrypted_api_key = new_cipher.encrypt(decrypted)
                db.commit()
            
            encryptor.rotate_key(new_key, migrate_credentials)
        """
        old_cipher = self.cipher
        new_cipher = Fernet(new_master_key.encode())
        
        try:
            # Execute migration callback
            re_encrypt_data(old_cipher, new_cipher)
            
            # Update current key
            self.master_key = new_master_key
            self.cipher = new_cipher
            self.multi_cipher = new_cipher
            
            # Add old key to legacy list
            old_key_str = old_cipher._encryption_key.decode()
            if old_key_str not in self.legacy_keys:
                self.legacy_keys.insert(0, old_key_str)
            
            print(f"? Key rotation complete. Legacy keys: {len(self.legacy_keys)}")
        except Exception as e:
            raise EncryptionError(f"Key rotation failed: {e}")


# Global singleton instance
_encryptor: Optional[CredentialEncryptor] = None


def get_encryptor() -> CredentialEncryptor:
    """
    Get or create the global encryptor instance.
    
    Returns:
        CredentialEncryptor singleton
    """
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryptor()
    return _encryptor


def encrypt_credential(plaintext: str) -> str:
    """
    Convenience function to encrypt a credential.
    
    Args:
        plaintext: The credential to encrypt
    
    Returns:
        Encrypted string (base64-encoded)
    """
    return get_encryptor().encrypt(plaintext)


def decrypt_credential(ciphertext: str) -> str:
    """
    Convenience function to decrypt a credential.
    
    Args:
        ciphertext: Encrypted string
    
    Returns:
        Original plaintext credential
    """
    return get_encryptor().decrypt(ciphertext)


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded key string
    
    Usage:
        >>> key = generate_key()
        >>> print(f"Export this: MASTER_KEY={key}")
    """
    return Fernet.generate_key().decode("utf-8")


# Password hashing utilities (for user passwords, not for symmetric encryption)
def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive an encryption key from a user password using PBKDF2.
    
    This is for scenarios where encryption key is derived from user input
    (e.g., encrypted local backups).
    
    Args:
        password: User-provided password
        salt: Random salt (min 16 bytes)
    
    Returns:
        32-byte derived key suitable for Fernet
    """
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


if __name__ == "__main__":
    """
    CLI utility for key generation and testing.
    
    Usage:
        python -m backend.core.encryption generate
        python -m backend.core.encryption test
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backend.core.encryption [generate|test]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        key = generate_key()
        print(f"Generated MASTER_KEY:\n{key}")
        print("\nAdd to .env:")
        print(f"MASTER_KEY={key}")
    
    elif command == "test":
        if not os.getenv("MASTER_KEY"):
            print("? MASTER_KEY not set in environment")
            sys.exit(1)
        
        encryptor = get_encryptor()
        test_data = "my-secret-api-key-12345"
        
        encrypted = encryptor.encrypt(test_data)
        print(f"? Encrypted: {encrypted[:50]}...")
        
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == test_data, "Decryption mismatch!"
        print(f"? Decrypted: {decrypted}")
        print("? Encryption test passed")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
