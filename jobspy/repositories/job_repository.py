# jobspy/repositories/job_repository.py
"""
Job repository for job listing operations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from .base_repository import BaseRepository


class JobRepository(BaseRepository):
    """Repository for job operations."""

    def __init__(self):
        super().__init__("jobs")

    def upsert_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert or update job by external_id and site."""
        try:
            response = self.db.table(self.table_name)\
                .upsert(job_data, on_conflict="external_id,site")\
                .execute()
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as e:
            self.log.error(f"Error upserting job: {e}")
            raise

    def find_by_site(self, site: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Find jobs by site."""
        return self.find_by({"site": site}, limit=limit)

    def find_recent_jobs(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Find jobs posted in the last N days."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            response = self.db.table(self.table_name)\
                .select("*")\
                .gte("date_posted", str(cutoff_date))\
                .order("date_posted", desc=True)\
                .limit(limit)\
                .execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error finding recent jobs: {e}")
            return []

    def search_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        is_remote: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search jobs with filters."""
        try:
            query = self.db.table(self.table_name).select("*")

            if keywords:
                search_term = " | ".join(keywords)
                query = query.text_search("description", search_term)

            if location:
                query = query.ilike("location->>city", f"%{location}%")

            if is_remote is not None:
                query = query.eq("is_remote", is_remote)

            response = query.limit(limit).execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error searching jobs: {e}")
            return []

    def get_job_by_url(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Find job by URL."""
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("job_url", job_url)\
                .maybe_single()\
                .execute()
            return response.data
        except Exception as e:
            self.log.error(f"Error finding job by URL: {e}")
            return None

    def bulk_insert(self, jobs: List[Dict[str, Any]]) -> int:
        """Bulk insert jobs."""
        try:
            response = self.db.table(self.table_name)\
                .upsert(jobs, on_conflict="external_id,site")\
                .execute()
            count = len(response.data) if response.data else 0
            self.log.info(f"Bulk inserted {count} jobs")
            return count
        except Exception as e:
            self.log.error(f"Error bulk inserting jobs: {e}")
            return 0
