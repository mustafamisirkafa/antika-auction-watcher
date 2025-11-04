"""
Tests for credential encryption module (Sprint 2).
"""
import pytest
import os
from cryptography.fernet import Fernet

from backend.core.encryption import (
    CredentialEncryptor,
    encrypt_credential,
    decrypt_credential,
    generate_key,
    EncryptionError,
    derive_key_from_password,
)


@pytest.fixture
def test_master_key():
    """Generate a test master key."""
    return Fernet.generate_key().decode()


@pytest.fixture
def encryptor(test_master_key):
    """Create test encryptor instance."""
    return CredentialEncryptor(master_key=test_master_key)


class TestCredentialEncryptor:
    """Test suite for CredentialEncryptor class."""
    
    def test_encrypt_decrypt_basic(self, encryptor):
        """Test basic encryption and decryption."""
        plaintext = "my-secret-api-key-12345"
        
        encrypted = encryptor.encrypt(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)
        
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self, encryptor):
        """Test encrypting empty string."""
        encrypted = encryptor.encrypt("")
        assert encrypted == ""
        
        decrypted = encryptor.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_unicode(self, encryptor):
        """Test encrypting Unicode characters."""
        plaintext = "?ifr?-?????-??-??"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_decrypt_invalid_token(self, encryptor):
        """Test decrypting invalid ciphertext."""
        with pytest.raises(EncryptionError, match="Decryption failed"):
            encryptor.decrypt("invalid-ciphertext-xyz123")
    
    def test_decrypt_with_wrong_key(self, test_master_key):
        """Test decrypting with wrong key."""
        encryptor1 = CredentialEncryptor(master_key=test_master_key)
        other_key = Fernet.generate_key().decode()
        encryptor2 = CredentialEncryptor(master_key=other_key)
        
        plaintext = "secret-data"
        encrypted = encryptor1.encrypt(plaintext)
        
        with pytest.raises(EncryptionError):
            encryptor2.decrypt(encrypted)
    
    def test_multiple_encryptions_differ(self, encryptor):
        """Test that encrypting same plaintext produces different ciphertexts."""
        plaintext = "constant-secret"
        
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)
        
        # Fernet includes random IV, so ciphertexts differ
        assert encrypted1 != encrypted2
        
        # But both decrypt to same plaintext
        assert encryptor.decrypt(encrypted1) == plaintext
        assert encryptor.decrypt(encrypted2) == plaintext
    
    def test_no_master_key_raises_error(self):
        """Test that missing master key raises error."""
        # Temporarily clear env var
        original = os.getenv("MASTER_KEY")
        if "MASTER_KEY" in os.environ:
            del os.environ["MASTER_KEY"]
        
        try:
            with pytest.raises(EncryptionError, match="MASTER_KEY"):
                CredentialEncryptor()
        finally:
            # Restore original
            if original:
                os.environ["MASTER_KEY"] = original


class TestLegacyKeySupport:
    """Test key rotation and legacy key support."""
    
    def test_decrypt_with_legacy_key(self, test_master_key):
        """Test decrypting data encrypted with legacy key."""
        # Encrypt with old key
        old_key = test_master_key
        old_encryptor = CredentialEncryptor(master_key=old_key)
        plaintext = "old-encrypted-data"
        ciphertext = old_encryptor.encrypt(plaintext)
        
        # Create new encryptor with new key + old as legacy
        new_key = Fernet.generate_key().decode()
        os.environ["LEGACY_KEYS"] = old_key
        new_encryptor = CredentialEncryptor(master_key=new_key)
        
        # Should decrypt with legacy key
        decrypted = new_encryptor.decrypt(ciphertext)
        assert decrypted == plaintext
        
        # Cleanup
        del os.environ["LEGACY_KEYS"]


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_encrypt_decrypt_credential(self, test_master_key, monkeypatch):
        """Test convenience functions."""
        monkeypatch.setenv("MASTER_KEY", test_master_key)
        
        plaintext = "api-key-xyz"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)
        
        assert decrypted == plaintext
    
    def test_generate_key(self):
        """Test key generation."""
        key1 = generate_key()
        key2 = generate_key()
        
        # Keys are base64-encoded
        assert len(key1) > 20
        assert len(key2) > 20
        
        # Keys are unique
        assert key1 != key2
        
        # Keys are valid Fernet keys
        Fernet(key1.encode())  # Should not raise


class TestPasswordDerivedKeys:
    """Test password-based key derivation."""
    
    def test_derive_key_from_password(self):
        """Test PBKDF2 key derivation."""
        password = "UserPassword123!"
        salt = os.urandom(16)
        
        key = derive_key_from_password(password, salt)
        
        # Key should be 44 bytes (32 bytes + base64 padding)
        assert len(key) == 44
        
        # Same password + salt should produce same key
        key2 = derive_key_from_password(password, salt)
        assert key == key2
        
        # Different salt should produce different key
        salt2 = os.urandom(16)
        key3 = derive_key_from_password(password, salt2)
        assert key != key3
    
    def test_encrypt_with_derived_key(self):
        """Test encryption with password-derived key."""
        password = "SecretPassword!"
        salt = os.urandom(16)
        
        derived_key = derive_key_from_password(password, salt)
        encryptor = CredentialEncryptor(master_key=derived_key.decode())
        
        plaintext = "user-data"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_very_long_plaintext(self, encryptor):
        """Test encrypting very long strings."""
        plaintext = "A" * 100000  # 100KB
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_special_characters(self, encryptor):
        """Test encrypting special characters."""
        plaintext = r"!@#$%^&*()_+-=[]{}|;:',.<>?/~`\""
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_null_bytes(self, encryptor):
        """Test encrypting strings with null bytes."""
        plaintext = "before\x00after"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_store_and_retrieve_api_key(self, encryptor):
        """Simulate storing and retrieving an API key."""
        # User registers Instagram credentials
        api_key = "instagram_api_key_abc123xyz789"
        
        # Encrypt before storing in DB
        encrypted_key = encryptor.encrypt(api_key)
        
        # Simulate DB storage (string)
        assert isinstance(encrypted_key, str)
        
        # Retrieve and decrypt for API call
        decrypted_key = encryptor.decrypt(encrypted_key)
        assert decrypted_key == api_key
    
    def test_bulk_encryption(self, encryptor):
        """Test encrypting multiple credentials."""
        credentials = {
            "ebay": "ebay_key_123",
            "etsy": "etsy_secret_456",
            "instagram": "ig_token_789",
        }
        
        # Encrypt all
        encrypted = {k: encryptor.encrypt(v) for k, v in credentials.items()}
        
        # Decrypt all
        decrypted = {k: encryptor.decrypt(v) for k, v in encrypted.items()}
        
        assert decrypted == credentials


# Performance benchmark (optional)
@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks for encryption operations."""
    
    def test_encryption_speed(self, encryptor, benchmark):
        """Benchmark encryption speed."""
        plaintext = "test-api-key-" * 10
        
        result = benchmark(encryptor.encrypt, plaintext)
        assert len(result) > 0
    
    def test_decryption_speed(self, encryptor, benchmark):
        """Benchmark decryption speed."""
        plaintext = "test-api-key-" * 10
        ciphertext = encryptor.encrypt(plaintext)
        
        result = benchmark(encryptor.decrypt, ciphertext)
        assert result == plaintext
