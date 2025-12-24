# jobspy/api/models.py
"""
Pydantic models for API request/response validation.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class ProfileCreate(BaseModel):
    """Request model for creating a profile."""
    email: EmailStr
    full_name: Optional[str] = None
    resume_text: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: int = 0
    preferences: Dict[str, Any] = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    """Request model for updating a profile."""
    full_name: Optional[str] = None
    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None


class ProfileResponse(BaseModel):
    """Response model for profile data."""
    id: UUID
    email: str
    full_name: Optional[str]
    skills: List[str]
    experience_years: int
    created_at: datetime


class JobSearchRequest(BaseModel):
    """Request model for job search."""
    keywords: List[str] = Field(..., min_items=1)
    location: str = "India"
    sites: List[str] = Field(default=["linkedin", "naukri"])
    results_wanted: int = Field(default=100, ge=10, le=500)
    is_remote: bool = False
    auto_match: bool = True


class JobSearchResponse(BaseModel):
    """Response model for job search results."""
    search_id: UUID
    jobs_found: int
    jobs_saved: int
    match_stats: Optional[Dict[str, Any]] = None


class JobMatchResponse(BaseModel):
    """Response model for job match."""
    id: UUID
    job_id: UUID
    match_score: int
    alignment_level: str
    matching_skills: List[str]
    missing_skills: List[str]
    why_fits: str
    job: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Response model for job listing."""
    id: UUID
    external_id: str
    site: str
    title: str
    company_name: Optional[str]
    location: Dict[str, Any]
    job_url: str
    is_remote: bool
    date_posted: Optional[str]
    skills: List[str]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    timestamp: datetime
