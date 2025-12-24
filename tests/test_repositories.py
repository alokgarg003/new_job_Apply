# tests/test_repositories.py
"""
Tests for repository layer.
Note: These tests require a Supabase instance to be configured.
"""
import pytest
from uuid import uuid4
from jobspy.repositories import ProfileRepository, JobRepository


@pytest.mark.integration
def test_profile_repository_operations():
    """Test profile CRUD operations."""
    repo = ProfileRepository()

    profile_id = uuid4()
    email = f"test_{profile_id}@example.com"

    data = {
        "id": str(profile_id),
        "email": email,
        "full_name": "Test User",
        "skills": ["python", "linux"],
        "experience_years": 3
    }

    try:
        created = repo.create(data)
        assert created is not None
        assert created["email"] == email

        fetched = repo.get_by_id(profile_id)
        assert fetched is not None
        assert fetched["email"] == email

        updated = repo.update(profile_id, {"full_name": "Updated Name"})
        assert updated["full_name"] == "Updated Name"

    finally:
        repo.delete(profile_id)


@pytest.mark.integration
def test_job_repository_upsert():
    """Test job upsert functionality."""
    repo = JobRepository()

    job_data = {
        "external_id": f"test-{uuid4()}",
        "site": "linkedin",
        "title": "Test Job",
        "company_name": "Test Company",
        "job_url": "https://example.com/job/1",
        "location": {"city": "Bengaluru"},
        "skills": ["python"],
        "is_remote": False
    }

    try:
        job = repo.upsert_job(job_data)
        assert job is not None
        assert job["title"] == "Test Job"

        job_data["title"] = "Updated Test Job"
        updated = repo.upsert_job(job_data)
        assert updated["title"] == "Updated Test Job"

    finally:
        if job:
            repo.delete(uuid4(job["id"]))
