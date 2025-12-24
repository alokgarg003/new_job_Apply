# jobspy/repositories/__init__.py
"""
Repository layer for database operations using the repository pattern.
"""
from .profile_repository import ProfileRepository
from .job_repository import JobRepository
from .job_search_repository import JobSearchRepository
from .job_match_repository import JobMatchRepository

__all__ = [
    "ProfileRepository",
    "JobRepository",
    "JobSearchRepository",
    "JobMatchRepository"
]
