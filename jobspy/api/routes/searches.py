# jobspy/api/routes/searches.py
"""
Job search endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from jobspy.api.models import (
    JobSearchRequest,
    JobSearchResponse,
    JobMatchResponse,
    ErrorResponse
)
from jobspy.api.dependencies import get_job_search_service, get_current_user_id
from jobspy.services import JobSearchService

router = APIRouter()


@router.post(
    "/searches",
    response_model=JobSearchResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}}
)
async def create_search(
    search_request: JobSearchRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: JobSearchService = Depends(get_job_search_service)
):
    """
    Execute a new job search with scraping and matching.

    This endpoint:
    1. Scrapes jobs from specified sites
    2. Saves jobs to database
    3. Optionally matches jobs to user profile
    """
    try:
        result = service.execute_search(
            profile_id=user_id,
            keywords=search_request.keywords,
            location=search_request.location,
            sites=search_request.sites,
            results_wanted=search_request.results_wanted,
            is_remote=search_request.is_remote,
            auto_match=search_request.auto_match
        )

        return JobSearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/searches",
    response_model=List[dict]
)
async def get_my_searches(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=20, ge=1, le=100),
    service: JobSearchService = Depends(get_job_search_service)
):
    """Get current user's search history."""
    searches = service.get_user_searches(user_id, limit=limit)
    return searches


@router.get(
    "/searches/{search_id}/results",
    response_model=List[JobMatchResponse]
)
async def get_search_results(
    search_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
    service: JobSearchService = Depends(get_job_search_service)
):
    """Get matched results for a specific search."""
    try:
        results = service.get_search_results(search_id, min_score=min_score)
        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
