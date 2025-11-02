"""
Tests for Advisor API Router
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_suggestion_endpoint():
    """Test GET /advisor/suggest/{item_id}"""
    response = client.get("/api/v1/advisor/suggest/item123")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "item_id" in data
    assert "recommendation" in data
    assert "confidence" in data
    assert "risk_level" in data
    assert "reasoning" in data
    assert isinstance(data["reasoning"], list)


def test_batch_analysis_endpoint():
    """Test POST /advisor/analyze_batch"""
    payload = {
        "item_ids": ["item1", "item2", "item3"],
        "include_details": True
    }
    
    response = client.post("/api/v1/advisor/analyze_batch", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "recommendations" in data
    assert "total_analyzed" in data
    assert data["total_analyzed"] == 3
    assert len(data["recommendations"]) == 3


def test_feedback_endpoint():
    """Test POST /advisor/feedback"""
    payload = {
        "item_id": "item123",
        "recommendation_id": "rec456",
        "feedback_type": "helpful",
        "comment": "Great advice!"
    }
    
    response = client.post("/api/v1/advisor/feedback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "feedback_id" in data


def test_advisor_stats_endpoint():
    """Test GET /advisor/stats"""
    response = client.get("/api/v1/advisor/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_recommendations" in data
    assert "accuracy_rate" in data
    assert "recommendations_by_level" in data


def test_advisor_explanation_endpoint():
    """Test GET /advisor/explanation"""
    response = client.get("/api/v1/advisor/explanation")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "senses" in data
    assert len(data["senses"]) == 4
    assert "recommendation_levels" in data


def test_advisor_health_endpoint():
    """Test GET /advisor/health"""
    response = client.get("/api/v1/advisor/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "advisor"
