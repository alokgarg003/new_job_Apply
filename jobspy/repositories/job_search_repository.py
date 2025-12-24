# jobspy/repositories/job_search_repository.py
"""
Job search repository for tracking search operations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from .base_repository import BaseRepository


class JobSearchRepository(BaseRepository):
    """Repository for job search operations."""

    def __init__(self):
        super().__init__("job_searches")

    def create_search(
        self,
        profile_id: UUID,
        keywords: List[str],
        location: str,
        sites: List[str],
        results_wanted: int
    ) -> Optional[Dict[str, Any]]:
        """Create a new job search."""
        data = {
            "profile_id": str(profile_id),
            "keywords": keywords,
            "location": location,
            "sites": sites,
            "results_wanted": results_wanted,
            "status": "pending"
        }
        return self.create(data)

    def update_status(
        self,
        search_id: UUID,
        status: str,
        jobs_found: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update search status."""
        try:
            data: Dict[str, Any] = {"status": status}
            if jobs_found is not None:
                data["jobs_found"] = jobs_found
            if error_message:
                data["error_message"] = error_message
            if status == "completed":
                data["completed_at"] = datetime.now().isoformat()

            self.update(search_id, data)
            return True
        except Exception as e:
            self.log.error(f"Error updating search status: {e}")
            return False

    def get_user_searches(
        self,
        profile_id: UUID,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's search history."""
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("profile_id", str(profile_id))\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error fetching user searches: {e}")
            return []

    def get_pending_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending searches for background processing."""
        return self.find_by({"status": "pending"}, limit=limit)
