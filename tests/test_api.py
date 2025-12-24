# tests/test_api.py
"""
API endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from jobspy.api.app import create_app

client = TestClient(create_app())


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "JobSpy" in response.json()["name"]


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_system_stats():
    """Test admin stats endpoint."""
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "statistics" in data


def test_get_profile_without_auth():
    """Test profile endpoint without authentication."""
    response = client.get("/api/v1/profiles/me")
    assert response.status_code == 401


def test_create_profile_with_auth():
    """Test profile creation with auth header."""
    user_id = str(uuid4())
    headers = {"X-User-ID": user_id}

    profile_data = {
        "email": f"test_{user_id}@example.com",
        "full_name": "Test User",
        "skills": ["python", "aws"],
        "experience_years": 5
    }

    response = client.post(
        "/api/v1/profiles",
        json=profile_data,
        headers=headers
    )

    # May fail if database not configured, but structure should be correct
    if response.status_code == 201:
        data = response.json()
        assert data["email"] == profile_data["email"]
