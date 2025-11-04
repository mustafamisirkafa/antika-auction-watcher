"""
Security Tests (Sprint 2)
Tests for encryption, JWT, rate limiting, and security headers.
"""
import pytest
import time
from datetime import timedelta
from unittest.mock import Mock, AsyncMock, patch

from backend.core.encryption import (
    EncryptionService,
    EncryptionError,
    CredentialRotation,
    encrypt_credential,
    decrypt_credential,
)
from backend.core.auth_enhanced import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    decode_token,
)
from backend.core.log_redaction import LogRedactor, redact
from backend.middleware.security_headers import SecurityHeadersMiddleware


# ==================== Encryption Tests ====================

def test_encryption_service_initialization():
    """Test encryption service initialization."""
    # Generate a test key
    key = EncryptionService.generate_key()
    
    # Initialize with key
    service = EncryptionService(master_key=key)
    assert service.cipher is not None


def test_encryption_service_missing_key():
    """Test encryption service fails without key."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(EncryptionError):
            EncryptionService()


def test_encrypt_decrypt_roundtrip():
    """Test encryption and decryption roundtrip."""
    key = EncryptionService.generate_key()
    service = EncryptionService(master_key=key)
    
    # Encrypt plaintext
    plaintext = "my-secret-api-key-12345"
    encrypted = service.encrypt(plaintext)
    
    # Encrypted should be different from plaintext
    assert encrypted != plaintext
    assert len(encrypted) > 0
    
    # Decrypt should recover original
    decrypted = service.decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_empty_string():
    """Test encrypting empty string."""
    key = EncryptionService.generate_key()
    service = EncryptionService(master_key=key)
    
    encrypted = service.encrypt("")
    assert encrypted == ""
    
    decrypted = service.decrypt("")
    assert decrypted == ""


def test_decrypt_invalid_token():
    """Test decrypting with wrong key fails."""
    key1 = EncryptionService.generate_key()
    key2 = EncryptionService.generate_key()
    
    service1 = EncryptionService(master_key=key1)
    service2 = EncryptionService(master_key=key2)
    
    # Encrypt with key1
    encrypted = service1.encrypt("secret")
    
    # Try to decrypt with key2 - should fail
    with pytest.raises(EncryptionError):
        service2.decrypt(encrypted)


def test_encrypt_decrypt_dict():
    """Test encrypting/decrypting dictionary fields."""
    key = EncryptionService.generate_key()
    service = EncryptionService(master_key=key)
    
    data = {
        "username": "john",
        "password": "secret123",
        "api_key": "sk-12345",
        "public_field": "visible",
    }
    
    # Encrypt sensitive fields
    encrypted = service.encrypt_dict(data, ["password", "api_key"])
    
    assert encrypted["username"] == "john"
    assert encrypted["public_field"] == "visible"
    assert encrypted["password"] != "secret123"
    assert encrypted["api_key"] != "sk-12345"
    
    # Decrypt fields
    decrypted = service.decrypt_dict(encrypted, ["password", "api_key"])
    
    assert decrypted["password"] == "secret123"
    assert decrypted["api_key"] == "sk-12345"


def test_credential_rotation():
    """Test credential encryption key rotation."""
    old_key = EncryptionService.generate_key()
    new_key = EncryptionService.generate_key()
    
    old_service = EncryptionService(master_key=old_key)
    
    # Encrypt with old key
    plaintext = "my-credential"
    encrypted_old = old_service.encrypt(plaintext)
    
    # Rotate to new key
    rotation = CredentialRotation(old_key, new_key)
    encrypted_new = rotation.rotate(encrypted_old)
    
    # Verify new encryption works with new key
    new_service = EncryptionService(master_key=new_key)
    decrypted = new_service.decrypt(encrypted_new)
    
    assert decrypted == plaintext


# ==================== JWT Authentication Tests ====================

def test_create_access_token():
    """Test creating access token."""
    user_id = "user123"
    token = create_access_token(user_id)
    
    assert token is not None
    assert len(token) > 0
    assert token.count('.') == 2  # JWT has 3 parts


def test_create_refresh_token():
    """Test creating refresh token."""
    user_id = "user123"
    token = create_refresh_token(user_id)
    
    assert token is not None
    assert len(token) > 0


def test_decode_access_token():
    """Test decoding access token."""
    user_id = "user123"
    token = create_access_token(user_id)
    
    payload = decode_token(token)
    
    assert payload["sub"] == user_id
    assert payload["token_type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_refresh_token():
    """Test decoding refresh token."""
    user_id = "user123"
    token = create_refresh_token(user_id)
    
    payload = decode_token(token)
    
    assert payload["sub"] == user_id
    assert payload["token_type"] == "refresh"


def test_verify_access_token():
    """Test verifying access token."""
    user_id = "user123"
    token = create_access_token(user_id)
    
    verified_user_id = verify_access_token(token)
    
    assert verified_user_id == user_id


def test_verify_refresh_token():
    """Test verifying refresh token."""
    user_id = "user123"
    token = create_refresh_token(user_id)
    
    verified_user_id = verify_refresh_token(token)
    
    assert verified_user_id == user_id


def test_expired_token():
    """Test expired token is rejected."""
    from fastapi import HTTPException
    
    user_id = "user123"
    
    # Create token with negative expiration (already expired)
    token = create_access_token(
        user_id,
        expires_delta=timedelta(seconds=-10)
    )
    
    # Should raise HTTPException for expired token
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    
    assert exc_info.value.status_code == 401


def test_token_with_user_agent_binding():
    """Test token with user-agent binding."""
    user_id = "user123"
    user_agent = "Mozilla/5.0 Test Browser"
    
    token = create_access_token(user_id, user_agent=user_agent)
    payload = decode_token(token)
    
    assert "ua_hash" in payload
    assert len(payload["ua_hash"]) > 0


def test_token_with_ip_binding():
    """Test token with IP address binding."""
    user_id = "user123"
    ip_address = "192.168.1.100"
    
    token = create_access_token(user_id, ip_address=ip_address)
    payload = decode_token(token)
    
    assert "ip_hash" in payload
    assert len(payload["ip_hash"]) > 0


# ==================== Log Redaction Tests ====================

def test_redact_jwt_token():
    """Test JWT token redaction."""
    redactor = LogRedactor()
    
    text = "User authenticated with token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    redacted = redactor.redact_text(text)
    
    assert "[REDACTED_JWT]" in redacted
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted


def test_redact_api_key():
    """Test API key redaction."""
    redactor = LogRedactor()
    
    text = "API Key: api_key=sk-1234567890abcdefghijklmnop"
    
    redacted = redactor.redact_text(text)
    
    assert "[REDACTED_API_KEY]" in redacted
    assert "sk-1234567890abcdefghijklmnop" not in redacted


def test_redact_password():
    """Test password redaction."""
    redactor = LogRedactor()
    
    text = "Login failed for user with password=MySecretPass123"
    
    redacted = redactor.redact_text(text)
    
    assert "[REDACTED]" in redacted
    assert "MySecretPass123" not in redacted


def test_redact_email():
    """Test email partial redaction."""
    redactor = LogRedactor()
    
    text = "Email sent to john.doe@example.com"
    
    redacted = redactor.redact_text(text)
    
    # Should partially redact (keep first/last char + domain)
    assert "john.doe" not in redacted
    assert "@example.com" in redacted
    assert "j***e@example.com" in redacted


def test_redact_ip_address():
    """Test IP address partial redaction."""
    redactor = LogRedactor()
    
    text = "Request from IP: 192.168.1.100"
    
    redacted = redactor.redact_text(text)
    
    # Should redact last 2 octets
    assert "192.168" in redacted
    assert "192.168.1.100" not in redacted
    assert "xxx" in redacted


def test_redact_credit_card():
    """Test credit card number redaction."""
    redactor = LogRedactor()
    
    text = "Credit card: 4532-1234-5678-9010"
    
    redacted = redactor.redact_text(text)
    
    assert "[REDACTED_CC]" in redacted
    assert "4532-1234-5678-9010" not in redacted


def test_redact_dict_sensitive_fields():
    """Test dictionary field redaction."""
    redactor = LogRedactor()
    
    data = {
        "username": "john",
        "password": "secret123",
        "token": "abc123",
        "public_info": "visible",
    }
    
    redacted = redactor.redact_dict(data)
    
    assert redacted["username"] == "john"
    assert redacted["public_info"] == "visible"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"


def test_redact_nested_dict():
    """Test nested dictionary redaction."""
    redactor = LogRedactor()
    
    data = {
        "user": {
            "username": "john",
            "credentials": {
                "password": "secret",
                "api_key": "sk-12345"
            }
        }
    }
    
    redacted = redactor.redact_dict(data)
    
    assert redacted["user"]["username"] == "john"
    assert redacted["user"]["credentials"]["password"] == "[REDACTED]"
    assert redacted["user"]["credentials"]["api_key"] == "[REDACTED]"


def test_redact_convenience_function():
    """Test convenience redact function."""
    text = "Password: secret123, API Key: sk-12345"
    
    redacted = redact(text)
    
    assert "[REDACTED]" in redacted
    assert "secret123" not in redacted


# ==================== Security Headers Tests ====================

def test_security_headers_added():
    """Test security headers are added to response."""
    from fastapi import FastAPI, Response
    from starlette.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    
    assert "X-XSS-Protection" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_hsts_header_on_https():
    """Test HSTS header is added for HTTPS requests."""
    from fastapi import FastAPI, Request
    from starlette.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint(request: Request):
        return {"scheme": request.url.scheme}
    
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/test")
    
    # HSTS should be present for HTTPS
    assert "Strict-Transport-Security" in response.headers


# ==================== Rate Limiting Tests (Conceptual) ====================

def test_rate_limit_key_extraction():
    """Test rate limit key extraction from request."""
    from backend.middleware.rate_limiting import get_user_or_ip_key
    from fastapi import Request
    
    # Mock request without auth
    mock_request = Mock(spec=Request)
    mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
    mock_request.client = Mock(host="192.168.1.1")
    
    key = get_user_or_ip_key(mock_request)
    
    assert key.startswith("ip:")
    assert "192.168.1.1" in key


@pytest.mark.asyncio
async def test_token_refresh_flow():
    """Test token refresh flow."""
    from backend.core.auth_enhanced import (
        create_refresh_token,
        verify_refresh_token,
        store_refresh_token,
        verify_stored_refresh_token,
    )
    
    # Mock Redis
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock(return_value=b"test_token")
    
    user_id = "user123"
    
    # Create refresh token
    token = create_refresh_token(user_id)
    
    # Verify token structure
    verified_user_id = verify_refresh_token(token)
    assert verified_user_id == user_id
    
    # Store token
    await store_refresh_token(user_id, token, redis_mock)
    redis_mock.setex.assert_called_once()
    
    # Verify stored token
    redis_mock.get.return_value = token.encode()
    is_valid = await verify_stored_refresh_token(user_id, token, redis_mock)
    assert is_valid is True
