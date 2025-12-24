# jobspy/services/job_search_service.py
"""
Job search orchestration service.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from jobspy.repositories import JobSearchRepository
from jobspy.services.job_scraper_service import JobScraperService
from jobspy.services.matching_service import MatchingService
from jobspy.util import create_logger

log = create_logger("JobSearchService")


class JobSearchService:
    """Service for orchestrating job searches end-to-end."""

    def __init__(self):
        self.search_repo = JobSearchRepository()
        self.scraper_service = JobScraperService()
        self.matching_service = MatchingService()

    def execute_search(
        self,
        profile_id: UUID,
        keywords: List[str],
        location: str = "India",
        sites: Optional[List[str]] = None,
        results_wanted: int = 100,
        is_remote: bool = False,
        auto_match: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a complete job search with scraping and matching.

        Args:
            profile_id: User profile ID
            keywords: Search keywords
            location: Job location
            sites: Job boards to search
            results_wanted: Number of results
            is_remote: Filter for remote jobs
            auto_match: Automatically match scraped jobs

        Returns:
            Dict with search results and match statistics
        """
        log.info(f"Executing search for profile {profile_id}: {keywords}")

        scrape_result = self.scraper_service.scrape_and_save(
            profile_id=profile_id,
            keywords=keywords,
            location=location,
            sites=sites,
            results_wanted=results_wanted,
            is_remote=is_remote
        )

        search_id = UUID(scrape_result["search_id"])
        result = {
            "search_id": str(search_id),
            "jobs_found": scrape_result["jobs_found"],
            "jobs_saved": scrape_result["jobs_saved"]
        }

        if auto_match and scrape_result["jobs_saved"] > 0:
            log.info(f"Matching jobs for search {search_id}")
            match_result = self.matching_service.match_jobs_for_search(
                profile_id=profile_id,
                search_id=search_id
            )
            result["match_stats"] = match_result

        return result

    def get_search_results(
        self,
        search_id: UUID,
        min_score: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get matched results for a search."""
        from jobspy.repositories import JobMatchRepository
        match_repo = JobMatchRepository()
        return match_repo.get_matches_by_search(search_id, min_score)

    def get_user_searches(
        self,
        profile_id: UUID,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's search history."""
        return self.search_repo.get_user_searches(profile_id, limit=limit)
