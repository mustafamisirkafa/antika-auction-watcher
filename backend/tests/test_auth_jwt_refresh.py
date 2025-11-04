"""
Tests for JWT refresh token authentication (Sprint 2).
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from jose import jwt

from backend.core.auth_enhanced import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    store_refresh_token,
    verify_stored_refresh_token,
    revoke_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_HOURS,
    ALGORITHM,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = MagicMock()
    request.headers = {
        "User-Agent": "Mozilla/5.0 Test Browser",
        "X-Forwarded-For": "192.168.1.100"
    }
    request.client.host = "192.168.1.100"
    return request


class TestAccessTokenCreation:
    """Test access token creation and verification."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        user_id = "123"
        token = create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
    
    def test_access_token_payload(self):
        """Test access token contains correct payload."""
        user_id = "456"
        token = create_access_token(user_id)
        
        # Decode without verification (for testing)
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        assert payload["sub"] == user_id
        assert payload["token_type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_access_token_expiration(self):
        """Test access token expiration time."""
        user_id = "789"
        token = create_access_token(user_id)
        
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        
        # Should expire in ~1 hour
        delta = exp_time - iat_time
        assert 59 <= delta.total_seconds() / 60 <= 61  # ~60 minutes
    
    def test_access_token_with_user_agent(self):
        """Test access token with user-agent binding."""
        user_id = "123"
        user_agent = "Mozilla/5.0"
        
        token = create_access_token(user_id, user_agent=user_agent)
        
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        assert "ua_hash" in payload
        assert len(payload["ua_hash"]) == 16  # SHA-256 first 16 chars
    
    def test_access_token_with_ip_address(self):
        """Test access token with IP address binding."""
        user_id = "123"
        ip = "192.168.1.1"
        
        token = create_access_token(user_id, ip_address=ip)
        
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        assert "ip_hash" in payload


class TestRefreshTokenCreation:
    """Test refresh token creation and verification."""
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user_id = "123"
        token = create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_refresh_token_payload(self):
        """Test refresh token contains correct payload."""
        user_id = "456"
        token = create_refresh_token(user_id)
        
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        assert payload["sub"] == user_id
        assert payload["token_type"] == "refresh"
    
    def test_refresh_token_expiration(self):
        """Test refresh token expires in 24 hours."""
        user_id = "789"
        token = create_refresh_token(user_id)
        
        from backend.core.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        
        # Should expire in ~24 hours
        delta = exp_time - iat_time
        assert 23.5 <= delta.total_seconds() / 3600 <= 24.5  # ~24 hours


class TestTokenVerification:
    """Test token verification logic."""
    
    def test_verify_access_token_valid(self):
        """Test verifying valid access token."""
        user_id = "123"
        token = create_access_token(user_id)
        
        verified_user_id = verify_access_token(token)
        assert verified_user_id == user_id
    
    def test_verify_access_token_invalid_type(self):
        """Test verifying refresh token as access token fails."""
        user_id = "123"
        token = create_refresh_token(user_id)  # Wrong type
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(token)
        
        assert exc_info.value.status_code == 401
    
    def test_verify_refresh_token_valid(self):
        """Test verifying valid refresh token."""
        user_id = "456"
        token = create_refresh_token(user_id)
        
        verified_user_id = verify_refresh_token(token)
        assert verified_user_id == user_id
    
    def test_verify_refresh_token_invalid_type(self):
        """Test verifying access token as refresh token fails."""
        user_id = "456"
        token = create_access_token(user_id)  # Wrong type
        
        with pytest.raises(HTTPException) as exc_info:
            verify_refresh_token(token)
        
        assert exc_info.value.status_code == 401
    
    def test_verify_expired_token(self):
        """Test verifying expired token fails."""
        user_id = "789"
        
        # Create token that expires immediately
        token = create_access_token(
            user_id,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(token)
        
        assert exc_info.value.status_code == 401
    
    def test_verify_malformed_token(self):
        """Test verifying malformed token fails."""
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token("not-a-valid-jwt-token")
        
        assert exc_info.value.status_code == 401


class TestSecurityBinding:
    """Test user-agent and IP binding for tokens."""
    
    def test_user_agent_binding_success(self, mock_request):
        """Test user-agent binding allows matching requests."""
        user_id = "123"
        user_agent = mock_request.headers["User-Agent"]
        
        token = create_access_token(user_id, user_agent=user_agent)
        
        verified_user_id = verify_access_token(token, mock_request)
        assert verified_user_id == user_id
    
    def test_user_agent_binding_failure(self, mock_request):
        """Test user-agent binding rejects mismatched requests."""
        user_id = "123"
        user_agent = "Original Browser"
        
        token = create_access_token(user_id, user_agent=user_agent)
        
        # Change user-agent
        mock_request.headers["User-Agent"] = "Different Browser"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(token, mock_request)
        
        assert exc_info.value.status_code == 401
    
    def test_ip_binding_success(self, mock_request):
        """Test IP binding allows matching requests."""
        user_id = "456"
        ip = "192.168.1.100"
        
        token = create_access_token(user_id, ip_address=ip)
        
        verified_user_id = verify_access_token(token, mock_request)
        assert verified_user_id == user_id
    
    def test_ip_binding_failure(self, mock_request):
        """Test IP binding rejects mismatched requests."""
        user_id = "456"
        ip = "192.168.1.100"
        
        token = create_access_token(user_id, ip_address=ip)
        
        # Change IP
        mock_request.headers["X-Forwarded-For"] = "10.0.0.1"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(token, mock_request)
        
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestRedisTokenStorage:
    """Test Redis-based refresh token storage."""
    
    async def test_store_refresh_token(self, mock_redis):
        """Test storing refresh token in Redis."""
        user_id = "123"
        token = create_refresh_token(user_id)
        
        await store_refresh_token(user_id, token, mock_redis)
        
        # Verify Redis setex was called
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == f"refresh_token:{user_id}"
        assert args[1] == REFRESH_TOKEN_EXPIRE_HOURS * 3600
        assert args[2] == token
    
    async def test_verify_stored_refresh_token_valid(self, mock_redis):
        """Test verifying stored refresh token."""
        user_id = "456"
        token = create_refresh_token(user_id)
        
        # Mock Redis returning the token
        mock_redis.get.return_value = token.encode()
        
        is_valid = await verify_stored_refresh_token(user_id, token, mock_redis)
        assert is_valid is True
    
    async def test_verify_stored_refresh_token_invalid(self, mock_redis):
        """Test verifying invalid stored refresh token."""
        user_id = "789"
        token = create_refresh_token(user_id)
        different_token = create_refresh_token(user_id)
        
        # Mock Redis returning different token
        mock_redis.get.return_value = different_token.encode()
        
        is_valid = await verify_stored_refresh_token(user_id, token, mock_redis)
        assert is_valid is False
    
    async def test_verify_stored_refresh_token_not_found(self, mock_redis):
        """Test verifying refresh token when none is stored."""
        user_id = "999"
        token = create_refresh_token(user_id)
        
        # Mock Redis returning None (token not found)
        mock_redis.get.return_value = None
        
        is_valid = await verify_stored_refresh_token(user_id, token, mock_redis)
        assert is_valid is False
    
    async def test_revoke_refresh_token(self, mock_redis):
        """Test revoking refresh token."""
        user_id = "321"
        
        await revoke_refresh_token(user_id, mock_redis)
        
        # Verify Redis delete was called
        mock_redis.delete.assert_called_once_with(f"refresh_token:{user_id}")


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test complete authentication flows."""
    
    async def test_login_and_refresh_flow(self, mock_redis):
        """Test complete login ? refresh flow."""
        user_id = "123"
        user_agent = "Test Browser"
        ip = "192.168.1.1"
        
        # 1. Login: Create tokens
        access_token = create_access_token(user_id, user_agent, ip)
        refresh_token = create_refresh_token(user_id, user_agent, ip)
        
        # 2. Store refresh token
        await store_refresh_token(user_id, refresh_token, mock_redis)
        
        # 3. Use access token (verify)
        verified_user = verify_access_token(access_token)
        assert verified_user == user_id
        
        # 4. Refresh: Verify refresh token
        mock_redis.get.return_value = refresh_token.encode()
        verified_refresh_user = verify_refresh_token(refresh_token)
        assert verified_refresh_user == user_id
        
        # 5. Issue new access token
        new_access_token = create_access_token(user_id, user_agent, ip)
        assert new_access_token != access_token
    
    async def test_logout_flow(self, mock_redis):
        """Test logout flow (revoke refresh token)."""
        user_id = "456"
        refresh_token = create_refresh_token(user_id)
        
        # Store token
        await store_refresh_token(user_id, refresh_token, mock_redis)
        
        # Logout: Revoke token
        await revoke_refresh_token(user_id, mock_redis)
        
        # Verify token is no longer valid
        mock_redis.get.return_value = None
        is_valid = await verify_stored_refresh_token(user_id, refresh_token, mock_redis)
        assert is_valid is False


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_token_without_sub_claim(self):
        """Test token without 'sub' claim fails."""
        from backend.core.config import settings
        
        # Create token without 'sub'
        payload = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access"
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
        
        with pytest.raises(HTTPException):
            verify_access_token(token)
    
    def test_empty_user_id(self):
        """Test creating token with empty user ID."""
        # Should still work (validation happens elsewhere)
        token = create_access_token("")
        assert isinstance(token, str)
