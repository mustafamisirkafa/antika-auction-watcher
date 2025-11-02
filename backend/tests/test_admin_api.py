"""Tests for admin API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.db.analytics_models import CategoryMetrics, BidOutcome
from backend.db.models import User


def test_health_services_endpoint(client, session, auth_headers):
    """Test system health services endpoint."""
    response = client.get(
        "/api/v1/admin/health/services",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'services' in data
    assert 'overall_status' in data


def test_health_database_endpoint(client, auth_headers):
    """Test database health endpoint."""
    response = client.get(
        "/api/v1/admin/health/database",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'


def test_list_users_endpoint(client, session, auth_headers):
    """Test listing users."""
    response = client.get(
        "/api/v1/admin/users",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'users' in data
    assert isinstance(data['users'], list)


def test_update_user_endpoint(client, session, auth_headers):
    """Test updating user status."""
    # Create a user first
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Update user
    response = client.patch(
        f"/api/v1/admin/users/{user.id}",
        headers=auth_headers,
        json={"is_active": False}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['is_active'] is False


def test_analytics_overview_endpoint(client, session, auth_headers):
    """Test analytics overview endpoint."""
    response = client.get(
        "/api/v1/admin/analytics/overview",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data


def test_category_analytics_endpoint(client, session, auth_headers):
    """Test category analytics endpoint."""
    # Create test metrics
    metrics = CategoryMetrics(
        category='antiques',
        total_bids=50,
        win_rate=0.7,
        average_profit=150.0
    )
    session.add(metrics)
    session.commit()
    
    response = client.get(
        "/api/v1/admin/analytics/categories",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'categories' in data
    assert len(data['categories']) >= 1


def test_bid_analytics_endpoint(client, auth_headers):
    """Test bid analytics endpoint."""
    response = client.get(
        "/api/v1/admin/analytics/bids?days=7",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'time_series' in data
    assert data['period_days'] == 7


def test_profitability_analytics_endpoint(client, session, auth_headers):
    """Test profitability analytics endpoint."""
    # Create metrics
    metrics = CategoryMetrics(
        category='jewelry',
        total_profit=5000.0,
        average_roi=0.25
    )
    session.add(metrics)
    session.commit()
    
    response = client.get(
        "/api/v1/admin/analytics/profitability",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'total_profit' in data
    assert 'categories' in data


def test_response_times_metrics_endpoint(client, auth_headers):
    """Test response times metrics endpoint."""
    response = client.get(
        "/api/v1/admin/metrics/response-times?hours=1",
        headers=auth_headers
    )
    
    assert response.status_code == 200


def test_api_usage_metrics_endpoint(client, auth_headers):
    """Test API usage metrics endpoint."""
    response = client.get(
        "/api/v1/admin/metrics/api-usage?hours=24",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'period_hours' in data


def test_cache_metrics_endpoint(client, auth_headers):
    """Test cache metrics endpoint."""
    response = client.get(
        "/api/v1/admin/metrics/cache",
        headers=auth_headers
    )
    
    assert response.status_code == 200


def test_slow_queries_endpoint(client, auth_headers):
    """Test slow queries endpoint."""
    response = client.get(
        "/api/v1/admin/metrics/slow-queries?threshold_ms=50",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'slow_queries' in data
    assert 'threshold_ms' in data


def test_metrics_dashboard_endpoint(client, auth_headers):
    """Test comprehensive metrics dashboard."""
    response = client.get(
        "/api/v1/admin/metrics/dashboard",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'response_times' in data
    assert 'cache_performance' in data


def test_train_category_model_endpoint(client, auth_headers):
    """Test training category model endpoint."""
    response = client.post(
        "/api/v1/admin/learning/train/antiques",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data


def test_train_all_models_endpoint(client, auth_headers):
    """Test training all models endpoint."""
    response = client.post(
        "/api/v1/admin/learning/train-all",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'completed'


def test_learning_recommendations_endpoint(client, auth_headers):
    """Test learning recommendations endpoint."""
    response = client.get(
        "/api/v1/admin/learning/recommendations/jewelry",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'has_recommendations' in data


def test_get_configuration_endpoint(client, auth_headers):
    """Test getting configuration."""
    response = client.get(
        "/api/v1/admin/config",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'rate_limit_enabled' in data
    assert 'cache_ttl_seconds' in data


def test_audit_log_endpoint(client, auth_headers):
    """Test audit log endpoint (placeholder)."""
    response = client.get(
        "/api/v1/admin/audit-log",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'logs' in data


def test_cleanup_metrics_endpoint(client, auth_headers):
    """Test metrics cleanup endpoint."""
    response = client.post(
        "/api/v1/admin/system/cleanup-metrics?days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'


def test_admin_endpoint_requires_auth(client):
    """Test that admin endpoints require authentication."""
    response = client.get("/api/v1/admin/health/services")
    
    assert response.status_code == 401


def test_update_nonexistent_user(client, auth_headers):
    """Test updating non-existent user."""
    response = client.patch(
        "/api/v1/admin/users/99999",
        headers=auth_headers,
        json={"is_active": False}
    )
    
    assert response.status_code == 404
