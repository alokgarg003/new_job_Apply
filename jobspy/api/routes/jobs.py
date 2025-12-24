# jobspy/api/routes/jobs.py
"""
Job listing endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from jobspy.api.models import JobResponse, JobMatchResponse, ErrorResponse
from jobspy.api.dependencies import (
    get_scraper_service,
    get_matching_service,
    get_current_user_id
)
from jobspy.services import JobScraperService, MatchingService

router = APIRouter()


@router.get(
    "/jobs/recent",
    response_model=List[JobResponse]
)
async def get_recent_jobs(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
    service: JobScraperService = Depends(get_scraper_service)
):
    """Get recently scraped jobs."""
    jobs = service.get_recent_jobs(days=days, limit=limit)
    return jobs


@router.get(
    "/jobs/search",
    response_model=List[JobResponse]
)
async def search_jobs(
    keywords: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    is_remote: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: JobScraperService = Depends(get_scraper_service)
):
    """Search existing jobs in database."""
    keyword_list = None
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(",")]

    jobs = service.search_jobs(
        keywords=keyword_list,
        location=location,
        is_remote=is_remote,
        limit=limit
    )
    return jobs


@router.get(
    "/jobs/matches",
    response_model=List[JobMatchResponse]
)
async def get_my_top_matches(
    user_id: UUID = Depends(get_current_user_id),
    min_score: int = Query(default=45, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=100),
    service: MatchingService = Depends(get_matching_service)
):
    """Get top job matches for current user."""
    matches = service.get_top_matches(
        profile_id=user_id,
        min_score=min_score,
        limit=limit
    )
    return matches


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_job(
    job_id: UUID,
    service: JobScraperService = Depends(get_scraper_service)
):
    """Get a specific job by ID."""
    from jobspy.repositories import JobRepository

    job_repo = JobRepository()
    job = job_repo.get_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return JobResponse(**job)
