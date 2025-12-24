# tests/conftest.py
"""
Pytest configuration and fixtures.
"""
import pytest
from uuid import uuid4
from jobspy.config import reset_config, get_config
from jobspy.services import ProfileService
import os


@pytest.fixture(scope="session")
def test_config():
    """Configure test environment."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    reset_config()
    return get_config()


@pytest.fixture
def profile_service():
    """Provide ProfileService instance."""
    return ProfileService()


@pytest.fixture
def test_profile(profile_service):
    """Create a test profile."""
    profile_id = uuid4()
    email = f"test_{profile_id}@example.com"

    profile = profile_service.create_profile(
        profile_id=profile_id,
        email=email,
        full_name="Test User",
        skills=["python", "linux", "aws"],
        experience_years=5
    )

    yield profile

    # Cleanup would go here if needed


@pytest.fixture
def sample_job_data():
    """Provide sample job data for testing."""
    return {
        "external_id": "test-job-123",
        "site": "linkedin",
        "title": "Senior DevOps Engineer",
        "company_name": "Test Company",
        "location": {"city": "Bengaluru", "state": "Karnataka", "country": "India"},
        "description": "Looking for DevOps engineer with Python, AWS, Linux experience.",
        "job_url": "https://example.com/job/123",
        "skills": ["python", "aws", "linux", "docker"],
        "is_remote": False,
        "date_posted": "2025-01-01"
    }
