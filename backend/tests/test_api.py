"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.db.models import User


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_register_user(client: TestClient, session):
    """Test user registration."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "password" not in data


def test_register_duplicate_user(client: TestClient, session):
    """Test registering duplicate user."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123"
    }
    
    # Register first time
    client.post("/api/v1/auth/register", json=user_data)
    
    # Try to register again
    response = client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 400


def test_login(client: TestClient, session):
    """Test user login."""
    # Register user first
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123"
    }
    client.post("/api/v1/auth/register", json=user_data)
    
    # Login
    login_data = {
        "username": "testuser",
        "password": "securepassword123"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient, session):
    """Test login with invalid credentials."""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == 401
