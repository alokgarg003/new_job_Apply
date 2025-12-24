# jobspy/api/routes/admin.py
"""
Admin endpoints for system management.
"""
from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
from datetime import datetime

from jobspy.database import get_db
from jobspy.config import get_config

router = APIRouter()


@router.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    db = get_db()

    stats = {}

    try:
        profile_count = db.table("profiles").select("id", count="exact").execute()
        stats["total_profiles"] = profile_count.count or 0
    except Exception:
        stats["total_profiles"] = 0

    try:
        job_count = db.table("jobs").select("id", count="exact").execute()
        stats["total_jobs"] = job_count.count or 0
    except Exception:
        stats["total_jobs"] = 0

    try:
        search_count = db.table("job_searches").select("id", count="exact").execute()
        stats["total_searches"] = search_count.count or 0
    except Exception:
        stats["total_searches"] = 0

    try:
        match_count = db.table("job_matches").select("id", count="exact").execute()
        stats["total_matches"] = match_count.count or 0
    except Exception:
        stats["total_matches"] = 0

    return {
        "timestamp": datetime.now().isoformat(),
        "statistics": stats
    }


@router.get("/config")
async def get_system_config():
    """Get system configuration (sanitized)."""
    config = get_config()

    return {
        "environment": config.environment,
        "debug": config.debug,
        "log_level": config.log_level,
        "scraper": {
            "linkedin_delay": config.scraper.linkedin_delay,
            "naukri_delay": config.scraper.naukri_delay,
            "default_results": config.scraper.default_results_wanted
        },
        "matching": {
            "min_score": config.matching.min_score,
            "primary_skill_count": len(config.matching.primary_skills),
            "secondary_skill_count": len(config.matching.secondary_skills)
        }
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear application cache."""
    return {
        "status": "success",
        "message": "Cache cleared (not yet implemented)"
    }
