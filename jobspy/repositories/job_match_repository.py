# jobspy/repositories/job_match_repository.py
"""
Job match repository for storing and retrieving match scores.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from .base_repository import BaseRepository


class JobMatchRepository(BaseRepository):
    """Repository for job match operations."""

    def __init__(self):
        super().__init__("job_matches")

    def create_match(
        self,
        profile_id: UUID,
        job_id: UUID,
        search_id: UUID,
        match_score: int,
        alignment_level: str,
        matching_skills: List[str],
        missing_skills: List[str],
        match_reasons: List[str],
        why_fits: str
    ) -> Optional[Dict[str, Any]]:
        """Create a job match record."""
        data = {
            "profile_id": str(profile_id),
            "job_id": str(job_id),
            "search_id": str(search_id),
            "match_score": match_score,
            "alignment_level": alignment_level,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "match_reasons": match_reasons,
            "why_fits": why_fits
        }
        try:
            response = self.db.table(self.table_name)\
                .upsert(data, on_conflict="profile_id,job_id")\
                .execute()
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as e:
            self.log.error(f"Error creating match: {e}")
            raise

    def get_top_matches(
        self,
        profile_id: UUID,
        min_score: int = 45,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get top job matches for a profile."""
        try:
            response = self.db.table(self.table_name)\
                .select("*, jobs(*)")\
                .eq("profile_id", str(profile_id))\
                .gte("match_score", min_score)\
                .order("match_score", desc=True)\
                .limit(limit)\
                .execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error fetching top matches: {e}")
            return []

    def get_matches_by_search(
        self,
        search_id: UUID,
        min_score: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all matches for a specific search."""
        try:
            query = self.db.table(self.table_name)\
                .select("*, jobs(*)")\
                .eq("search_id", str(search_id))

            if min_score is not None:
                query = query.gte("match_score", min_score)

            response = query.order("match_score", desc=True).execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error fetching matches by search: {e}")
            return []

    def bulk_create_matches(self, matches: List[Dict[str, Any]]) -> int:
        """Bulk create match records."""
        try:
            response = self.db.table(self.table_name)\
                .upsert(matches, on_conflict="profile_id,job_id")\
                .execute()
            count = len(response.data) if response.data else 0
            self.log.info(f"Bulk created {count} matches")
            return count
        except Exception as e:
            self.log.error(f"Error bulk creating matches: {e}")
            return 0
