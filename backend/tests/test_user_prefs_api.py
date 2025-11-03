"""
Tests for User Preferences API (Phase 14).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": 1,
        "team_id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }


def test_get_user_prefs_unauthorized(client):
    """Test GET without authentication."""
    response = client.get("/api/user/prefs")
    
    assert response.status_code == 401


@patch("backend.routers.user_prefs.get_current_user")
@patch("backend.routers.user_prefs.get_user_prefs_service")
def test_get_user_prefs_success(mock_service, mock_get_user, client, mock_user):
    """Test GET with valid authentication."""
    # Mock authentication
    mock_get_user.return_value = mock_user
    
    # Mock service
    mock_svc = AsyncMock()
    mock_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["seller1:ebay"],
        "blocklist": ["seller2:etsy"],
        "updated_at": "2025-11-03T12:00:00Z"
    }
    mock_svc.get_user_preferences = AsyncMock(return_value=mock_prefs)
    mock_svc.parse_seller_list = MagicMock(side_effect=lambda x: [
        {"seller_id": s.split(":")[0], "source": s.split(":")[1], "reason": None}
        for s in x
    ])
    mock_service.return_value = mock_svc
    
    response = client.get(
        "/api/user/prefs",
        headers={"Authorization": "Bearer test_token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert len(data["allowlist"]) == 1
    assert len(data["blocklist"]) == 1


@patch("backend.routers.user_prefs.get_current_user")
@patch("backend.routers.user_prefs.get_user_prefs_service")
def test_update_user_prefs_add_block(mock_service, mock_get_user, client, mock_user):
    """Test POST to add seller to blocklist."""
    mock_get_user.return_value = mock_user
    
    mock_svc = AsyncMock()
    mock_svc.update_user_preference = AsyncMock(return_value={
        "success": True,
        "message": "Seller added to blocklist",
        "affected_list": "blocklist",
        "seller_id": "bad-seller",
        "new_total": 1,
        "updated_at": "2025-11-03T12:00:00Z"
    })
    mock_service.return_value = mock_svc
    
    response = client.post(
        "/api/user/prefs/update",
        headers={"Authorization": "Bearer test_token"},
        json={
            "action": "add_block",
            "seller_id": "bad-seller",
            "source": "ebay",
            "reason": "Low trust"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["affected_list"] == "blocklist"
    assert data["new_total"] == 1


@patch("backend.routers.user_prefs.get_current_user")
@patch("backend.routers.user_prefs.get_user_prefs_service")
def test_update_user_prefs_invalid_action(mock_service, mock_get_user, client, mock_user):
    """Test POST with invalid action."""
    mock_get_user.return_value = mock_user
    mock_service.return_value = AsyncMock()
    
    response = client.post(
        "/api/user/prefs/update",
        headers={"Authorization": "Bearer test_token"},
        json={
            "action": "invalid_action",
            "seller_id": "seller",
            "source": "ebay"
        }
    )
    
    assert response.status_code == 400


@patch("backend.routers.user_prefs.get_current_user")
@patch("backend.routers.user_prefs.get_user_prefs_service")
def test_check_seller_allowed(mock_service, mock_get_user, client, mock_user):
    """Test checking if seller is allowed."""
    mock_get_user.return_value = mock_user
    
    mock_svc = AsyncMock()
    mock_svc.check_seller_allowed = AsyncMock(return_value={
        "allowed": False,
        "reason": "Seller is blocklisted"
    })
    mock_service.return_value = mock_svc
    
    response = client.get(
        "/api/user/prefs/check/bad-seller?source=ebay",
        headers={"Authorization": "Bearer test_token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert "blocklisted" in data["reason"].lower()
