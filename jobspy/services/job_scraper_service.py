# jobspy/services/job_scraper_service.py
"""
Enhanced job scraping service with database persistence and deduplication.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from jobspy.repositories import JobRepository, JobSearchRepository
from jobspy.scrape_jobs import scrape_jobs
from jobspy.model import JobPost, Location, Country
from jobspy.config import get_config
from jobspy.util import create_logger
import pandas as pd

log = create_logger("JobScraperService")


class JobScraperService:
    """Service for job scraping with database integration."""

    def __init__(self):
        self.job_repo = JobRepository()
        self.search_repo = JobSearchRepository()
        self.config = get_config()

    def scrape_and_save(
        self,
        profile_id: UUID,
        keywords: List[str],
        location: str = "India",
        sites: Optional[List[str]] = None,
        results_wanted: int = 100,
        is_remote: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape jobs and save to database.

        Returns:
            Dict with search_id, jobs_found, jobs_saved
        """
        if sites is None:
            sites = ["linkedin", "naukri"]

        search_term = " OR ".join([f'"{k}"' for k in keywords])

        try:
            search_record = self.search_repo.create_search(
                profile_id=profile_id,
                keywords=keywords,
                location=location,
                sites=sites,
                results_wanted=results_wanted
            )

            if not search_record:
                raise Exception("Failed to create search record")

            search_id = UUID(search_record["id"])
            self.search_repo.update_status(search_id, "running")

            log.info(f"Starting scrape: {keywords} in {location} from {sites}")

            df = scrape_jobs(
                site_name=sites,
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                is_remote=is_remote,
                description_format=self.config.scraper.description_format
            )

            if df is None or df.empty:
                self.search_repo.update_status(
                    search_id,
                    "completed",
                    jobs_found=0
                )
                return {
                    "search_id": str(search_id),
                    "jobs_found": 0,
                    "jobs_saved": 0
                }

            jobs_data = self._prepare_jobs_for_db(df, search_id)
            jobs_saved = self.job_repo.bulk_insert(jobs_data)

            self.search_repo.update_status(
                search_id,
                "completed",
                jobs_found=len(df)
            )

            log.info(f"Scrape completed: {jobs_saved} jobs saved")

            return {
                "search_id": str(search_id),
                "jobs_found": len(df),
                "jobs_saved": jobs_saved,
                "jobs": jobs_data[:10]
            }

        except Exception as e:
            log.error(f"Scraping failed: {e}")
            if 'search_id' in locals():
                self.search_repo.update_status(
                    search_id,
                    "failed",
                    error_message=str(e)
                )
            raise

    def _prepare_jobs_for_db(
        self,
        df: pd.DataFrame,
        search_id: UUID
    ) -> List[Dict[str, Any]]:
        """Convert DataFrame to database-ready format."""
        jobs = []

        for _, row in df.iterrows():
            job_id = row.get("id")
            if not job_id:
                continue

            location_data = {}
            if "location" in row and pd.notna(row["location"]):
                location_str = str(row["location"])
                parts = [p.strip() for p in location_str.split(",")]
                if len(parts) >= 1:
                    location_data["city"] = parts[0]
                if len(parts) >= 2:
                    location_data["state"] = parts[1]
                if len(parts) >= 3:
                    location_data["country"] = parts[2]

            skills_list = []
            if "skills" in row and pd.notna(row["skills"]):
                skills_str = str(row["skills"])
                skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]

            job_data = {
                "external_id": str(job_id),
                "site": str(row.get("site", "unknown")),
                "title": str(row.get("title", ""))[:500],
                "company_name": str(row.get("company", ""))[:200] if pd.notna(row.get("company")) else None,
                "location": location_data,
                "description": str(row.get("description", ""))[:10000] if pd.notna(row.get("description")) else None,
                "job_url": str(row.get("job_url", "")),
                "job_type": str(row.get("job_type", ""))[:50] if pd.notna(row.get("job_type")) else None,
                "experience_range": str(row.get("experience_range", ""))[:100] if pd.notna(row.get("experience_range")) else None,
                "skills": skills_list,
                "is_remote": bool(row.get("is_remote", False)),
                "work_from_home_type": str(row.get("work_from_home_type", ""))[:50] if pd.notna(row.get("work_from_home_type")) else None,
                "date_posted": str(row["date_posted"]) if pd.notna(row.get("date_posted")) else None,
                "raw_data": row.to_dict()
            }

            if "min_amount" in row and pd.notna(row["min_amount"]):
                job_data["salary_min"] = float(row["min_amount"])
            if "max_amount" in row and pd.notna(row["max_amount"]):
                job_data["salary_max"] = float(row["max_amount"])
            if "currency" in row and pd.notna(row["currency"]):
                job_data["salary_currency"] = str(row["currency"])

            jobs.append(job_data)

        return jobs

    def get_recent_jobs(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently scraped jobs."""
        return self.job_repo.find_recent_jobs(days=days, limit=limit)

    def search_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        is_remote: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search existing jobs in database."""
        return self.job_repo.search_jobs(
            keywords=keywords,
            location=location,
            is_remote=is_remote,
            limit=limit
        )
