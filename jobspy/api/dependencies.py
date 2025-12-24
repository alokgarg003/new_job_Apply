# jobspy/api/dependencies.py
"""
FastAPI dependency injection for services and authentication.
"""
from typing import Optional
from fastapi import Header, HTTPException, status
from uuid import UUID
from jobspy.services import (
    ProfileService,
    JobSearchService,
    JobScraperService,
    MatchingService
)
from jobspy.config import get_config


def get_profile_service() -> ProfileService:
    """Dependency injection for ProfileService."""
    return ProfileService()


def get_job_search_service() -> JobSearchService:
    """Dependency injection for JobSearchService."""
    return JobSearchService()


def get_scraper_service() -> JobScraperService:
    """Dependency injection for JobScraperService."""
    return JobScraperService()


def get_matching_service() -> MatchingService:
    """Dependency injection for MatchingService."""
    return MatchingService()


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None)
) -> UUID:
    """
    Extract user ID from header.
    In production, this would validate JWT tokens.
    For now, accepting X-User-ID header for development.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required. Provide X-User-ID header."
        )

    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )


def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional API key validation for rate limiting.
    Returns None for public access.
    """
    return x_api_key
