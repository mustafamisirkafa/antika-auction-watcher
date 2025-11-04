"""
Credential Encryption Service (Sprint 2)
Uses Fernet (symmetric encryption) to protect sensitive credentials.
"""
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import base64

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """
    Handles encryption and decryption of sensitive credentials.
    Uses Fernet (AES-128-CBC) with a master key from environment.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            master_key: Base64-encoded Fernet key (32 bytes).
                       If None, reads from MASTER_KEY env var.
        
        Raises:
            ValueError: If master key is missing or invalid.
        """
        if master_key is None:
            master_key = os.getenv("MASTER_KEY")
        
        if not master_key:
            raise ValueError(
                "MASTER_KEY environment variable is required for encryption. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            # Validate and create Fernet cipher
            self.cipher = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
            logger.info("Credential encryption initialized successfully")
        except Exception as e:
            raise ValueError(f"Invalid MASTER_KEY format: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext credential.
        
        Args:
            plaintext: The credential to encrypt (password, token, etc.)
        
        Returns:
            Base64-encoded encrypted string
        
        Example:
            encrypted = encryptor.encrypt("my_secret_password")
            # Returns: "gAAAAABl..."
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            encrypted_str = encrypted_bytes.decode('utf-8')
            logger.debug("Credential encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted credential.
        
        Args:
            encrypted: Base64-encoded encrypted string
        
        Returns:
            Decrypted plaintext string
        
        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        
        Example:
            plaintext = encryptor.decrypt("gAAAAABl...")
            # Returns: "my_secret_password"
        """
        if not encrypted:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted.encode('utf-8'))
            plaintext = decrypted_bytes.decode('utf-8')
            logger.debug("Credential decrypted successfully")
            return plaintext
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or wrong key")
            raise ValueError("Failed to decrypt credential. Key may have changed.")
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
        
        Returns:
            Dictionary with specified fields encrypted
        
        Example:
            user = {"username": "john", "password": "secret123", "email": "john@example.com"}
            encrypted = encryptor.encrypt_dict(user, ["password"])
            # Result: {"username": "john", "password": "gAAAAABl...", "email": "john@example.com"}
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result
    
    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
        
        Returns:
            Dictionary with specified fields decrypted
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except Exception as e:
                    logger.warning(f"Failed to decrypt field '{field}': {e}")
                    result[field] = None
        return result
    
    def rotate_key(self, new_master_key: str, encrypted_values: list[str]) -> list[str]:
        """
        Rotate encryption key by re-encrypting existing values.
        
        Args:
            new_master_key: New base64-encoded Fernet key
            encrypted_values: List of values encrypted with old key
        
        Returns:
            List of values re-encrypted with new key
        
        Example:
            old_encrypted = ["gAAAAABl...", "gAAAAABm..."]
            new_encrypted = encryptor.rotate_key(new_key, old_encrypted)
        
        Note:
            1. Decrypt with current key
            2. Encrypt with new key
            3. Update database
            4. Update MASTER_KEY environment variable
        """
        # Create new cipher with new key
        new_cipher = Fernet(new_master_key.encode())
        
        rotated = []
        for encrypted_value in encrypted_values:
            try:
                # Decrypt with old key
                plaintext = self.decrypt(encrypted_value)
                # Re-encrypt with new key
                new_encrypted = new_cipher.encrypt(plaintext.encode('utf-8'))
                rotated.append(new_encrypted.decode('utf-8'))
            except Exception as e:
                logger.error(f"Key rotation failed for value: {e}")
                raise
        
        logger.info(f"Successfully rotated {len(rotated)} encrypted values")
        return rotated


# Global encryption instance
_encryptor: Optional[CredentialEncryption] = None


def get_encryptor() -> CredentialEncryption:
    """
    Get the global credential encryption instance.
    
    Returns:
        CredentialEncryption instance
    
    Raises:
        ValueError: If MASTER_KEY is not set
    """
    global _encryptor
    
    if _encryptor is None:
        _encryptor = CredentialEncryption()
    
    return _encryptor


def encrypt_credential(plaintext: str) -> str:
    """
    Convenience function to encrypt a credential.
    
    Args:
        plaintext: The credential to encrypt
    
    Returns:
        Encrypted string
    """
    return get_encryptor().encrypt(plaintext)


def decrypt_credential(encrypted: str) -> str:
    """
    Convenience function to decrypt a credential.
    
    Args:
        encrypted: The encrypted credential
    
    Returns:
        Decrypted plaintext
    """
    return get_encryptor().decrypt(encrypted)


def generate_master_key() -> str:
    """
    Generate a new Fernet master key.
    
    Returns:
        Base64-encoded Fernet key (32 bytes)
    
    Example:
        >>> key = generate_master_key()
        >>> print(key)
        'xJq7-dZk4vN8mP2wH3jK9sL6fT5bC1aE4gX7yU0hQ8='
    
    Usage:
        1. Generate key: python -c "from backend.core.encryption import generate_master_key; print(generate_master_key())"
        2. Add to .env: MASTER_KEY=<generated_key>
        3. Deploy with environment variable set
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


# Example usage in models:
"""
from backend.core.encryption import encrypt_credential, decrypt_credential

# Before saving to database
user.encrypted_password = encrypt_credential(plain_password)
user.instagram_token = encrypt_credential(instagram_token)

# When reading from database
plain_password = decrypt_credential(user.encrypted_password)
instagram_token = decrypt_credential(user.instagram_token)
"""
