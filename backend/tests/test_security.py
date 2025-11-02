"""Tests for security utilities."""
import pytest
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


def test_hash_password():
    """Test password hashing."""
    password = "test_password_123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_password():
    """Test password verification."""
    password = "test_password_123"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "123", "username": "testuser"}
    token = create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token():
    """Test JWT token decoding."""
    data = {"sub": "123", "username": "testuser"}
    token = create_access_token(data)
    
    decoded = decode_access_token(token)
    
    assert decoded is not None
    assert decoded["sub"] == "123"
    assert decoded["username"] == "testuser"
    assert "exp" in decoded


def test_decode_invalid_token():
    """Test decoding invalid token."""
    decoded = decode_access_token("invalid_token_here")
    assert decoded is None
