"""
Tests for User Preferences Service (Phase 14).
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.user_prefs_svc import UserPreferencesService
from backend.models.user_prefs import UserPreference


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.exec = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def service(mock_db, mock_redis, mock_event_bus):
    """Create UserPreferencesService instance."""
    return UserPreferencesService(mock_db, mock_redis, mock_event_bus)


@pytest.mark.asyncio
async def test_get_user_preferences_from_cache(service, mock_redis):
    """Test getting preferences from Redis cache."""
    import json
    
    cached_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["seller1:ebay"],
        "blocklist": ["seller2:etsy"],
        "updated_at": "2025-11-03T12:00:00Z"
    }
    
    mock_redis.get.return_value = json.dumps(cached_prefs)
    
    result = await service.get_user_preferences(1, 1)
    
    assert result == cached_prefs
    mock_redis.get.assert_called_once_with("user_prefs:1")


@pytest.mark.asyncio
async def test_get_user_preferences_from_db(service, mock_db, mock_redis):
    """Test getting preferences from database (cache miss)."""
    mock_redis.get.return_value = None
    
    db_prefs = UserPreference(
        id=1,
        user_id=1,
        team_id=1,
        allowlist=["seller1:ebay"],
        blocklist=["seller2:etsy"],
        updated_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    mock_result = MagicMock()
    mock_result.first.return_value = db_prefs
    mock_db.exec.return_value = mock_result
    
    result = await service.get_user_preferences(1, 1)
    
    assert isinstance(result, UserPreference)
    assert result.user_id == 1
    assert result.allowlist == ["seller1:ebay"]
    mock_redis.setex.assert_called_once()  # Should cache the result


@pytest.mark.asyncio
async def test_update_user_preference_add_block(service, mock_db, mock_redis, mock_event_bus):
    """Test adding seller to blocklist."""
    db_prefs = UserPreference(
        id=1,
        user_id=1,
        team_id=1,
        allowlist=[],
        blocklist=[],
        updated_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    mock_result = MagicMock()
    mock_result.first.return_value = db_prefs
    mock_db.exec.return_value = mock_result
    
    result = await service.update_user_preference(
        user_id=1,
        team_id=1,
        action="add_block",
        seller_id="bad-seller",
        source="ebay",
        reason="Low trust"
    )
    
    assert result["success"] is True
    assert result["affected_list"] == "blocklist"
    assert result["seller_id"] == "bad-seller"
    assert result["new_total"] == 1
    
    # Verify blocklist was updated
    assert "bad-seller:ebay" in db_prefs.blocklist
    
    # Verify cache was cleared and event emitted
    mock_redis.delete.assert_called_once_with("user_prefs:1")
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_preference_add_allow(service, mock_db, mock_redis, mock_event_bus):
    """Test adding seller to allowlist."""
    db_prefs = UserPreference(
        id=1,
        user_id=1,
        team_id=1,
        allowlist=[],
        blocklist=["bad-seller:ebay"],
        updated_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    mock_result = MagicMock()
    mock_result.first.return_value = db_prefs
    mock_db.exec.return_value = mock_result
    
    result = await service.update_user_preference(
        user_id=1,
        team_id=1,
        action="add_allow",
        seller_id="bad-seller",
        source="ebay"
    )
    
    assert result["success"] is True
    assert result["affected_list"] == "allowlist"
    
    # Verify seller was moved from blocklist to allowlist
    assert "bad-seller:ebay" in db_prefs.allowlist
    assert "bad-seller:ebay" not in db_prefs.blocklist


@pytest.mark.asyncio
async def test_check_seller_allowed_blocklisted(service, mock_redis):
    """Test checking blocklisted seller."""
    import json
    
    prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": [],
        "blocklist": ["bad-seller:ebay"]
    }
    
    mock_redis.get.return_value = json.dumps(prefs)
    
    result = await service.check_seller_allowed(1, 1, "bad-seller", "ebay")
    
    assert result["allowed"] is False
    assert "blocklist" in result["reason"].lower()


@pytest.mark.asyncio
async def test_check_seller_allowed_not_in_allowlist(service, mock_redis):
    """Test checking seller not in allowlist (restricted mode)."""
    import json
    
    prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["trusted-seller:ebay"],
        "blocklist": []
    }
    
    mock_redis.get.return_value = json.dumps(prefs)
    
    result = await service.check_seller_allowed(1, 1, "unknown-seller", "ebay")
    
    assert result["allowed"] is False
    assert "not in allowlist" in result["reason"].lower()


@pytest.mark.asyncio
async def test_check_seller_allowed_empty_lists(service, mock_redis):
    """Test checking seller with empty lists (default allow)."""
    import json
    
    prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": [],
        "blocklist": []
    }
    
    mock_redis.get.return_value = json.dumps(prefs)
    
    result = await service.check_seller_allowed(1, 1, "any-seller", "ebay")
    
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_parse_seller_list(service):
    """Test parsing seller list from storage format."""
    seller_keys = ["seller1:ebay", "seller2:etsy", "seller3:amazon"]
    
    items = service.parse_seller_list(seller_keys)
    
    assert len(items) == 3
    assert items[0].seller_id == "seller1"
    assert items[0].source == "ebay"
    assert items[1].seller_id == "seller2"
    assert items[1].source == "etsy"


@pytest.mark.asyncio
async def test_mutual_exclusion_add_allow_removes_from_block(service, mock_db, mock_redis, mock_event_bus):
    """Test that adding to allowlist removes from blocklist."""
    db_prefs = UserPreference(
        id=1,
        user_id=1,
        team_id=1,
        allowlist=[],
        blocklist=["seller-x:ebay"],
        updated_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    mock_result = MagicMock()
    mock_result.first.return_value = db_prefs
    mock_db.exec.return_value = mock_result
    
    await service.update_user_preference(
        user_id=1,
        team_id=1,
        action="add_allow",
        seller_id="seller-x",
        source="ebay"
    )
    
    # Verify mutual exclusion
    assert "seller-x:ebay" in db_prefs.allowlist
    assert "seller-x:ebay" not in db_prefs.blocklist
