# jobspy/api/routes/profiles.py
"""
Profile management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from jobspy.api.models import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ErrorResponse
)
from jobspy.api.dependencies import get_profile_service, get_current_user_id
from jobspy.services import ProfileService

router = APIRouter()


@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}}
)
async def create_profile(
    profile_data: ProfileCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service)
):
    """Create a new user profile."""
    try:
        existing = service.get_profile_by_email(profile_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile with this email already exists"
            )

        profile = service.create_profile(
            profile_id=user_id,
            **profile_data.model_dump()
        )

        return ProfileResponse(**profile)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/profiles/me",
    response_model=ProfileResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_my_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service)
):
    """Get current user's profile."""
    profile = service.get_profile(user_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return ProfileResponse(**profile)


@router.put(
    "/profiles/me",
    response_model=ProfileResponse
)
async def update_my_profile(
    updates: ProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service)
):
    """Update current user's profile."""
    update_data = {
        k: v for k, v in updates.model_dump().items()
        if v is not None
    }

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )

    profile = service.update_profile(user_id, update_data)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return ProfileResponse(**profile)


@router.post(
    "/profiles/me/parse-resume",
    response_model=dict
)
async def parse_resume(
    resume: dict,
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service)
):
    """Parse resume text to extract skills and experience."""
    resume_text = resume.get("resume_text", "")

    if not resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_text is required"
        )

    parsed_data = service.parse_resume(resume_text)

    if resume.get("auto_update", False):
        service.update_profile(user_id, parsed_data)

    return parsed_data
