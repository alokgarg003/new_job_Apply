# jobspy/model.py
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class JobType(Enum):
    FULL_TIME = "fulltime"
    PART_TIME = "parttime"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    PER_DIEM = "perdiem"
    NIGHTS = "nights"
    OTHER = "other"
    SUMMER = "summer"
    VOLUNTEER = "volunteer"

class Country(Enum):
    INDIA = "india"
    USA = "usa"
    # add others as needed

    @classmethod
    def from_string(cls, s):
        """Convert a string to a Country enum if possible. Returns the original string if unknown."""
        if s is None:
            return None
        s = str(s).strip()
        for member in cls:
            if s.lower() == member.value or s.lower() == member.name.lower():
                return member
        # Return the original string to allow location display for values like 'worldwide'
        return s

class CompensationInterval(str, Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"

class Compensation(BaseModel):
    interval: Optional[CompensationInterval] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = "USD"

class Location(BaseModel):
    country: Country | str | None = None
    city: Optional[str] = None
    state: Optional[str] = None

    def display_location(self) -> str:
        parts = []
        if self.city: parts.append(self.city)
        if self.state: parts.append(self.state)
        if isinstance(self.country, str): parts.append(self.country)
        elif self.country: parts.append(self.country.value.title())
        return ", ".join(parts)

class DescriptionFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"

class JobPost(BaseModel):
    id: Optional[str] = None
    title: str
    company_name: Optional[str] = None
    job_url: str
    job_url_direct: Optional[str] = None
    location: Optional[Location] = None
    description: Optional[str] = None
    company_url: Optional[str] = None
    company_url_direct: Optional[str] = None
    job_type: Optional[List[JobType]] = None
    compensation: Optional[Compensation] = None
    date_posted: Optional[date] = None
    emails: Optional[List[str]] = None
    is_remote: Optional[bool] = None
    listing_type: Optional[str] = None
    job_level: Optional[str] = None
    company_industry: Optional[str] = None
    company_addresses: Optional[str] = None
    company_num_employees: Optional[str] = None
    company_revenue: Optional[str] = None
    company_description: Optional[str] = None
    company_logo: Optional[str] = None
    banner_photo_url: Optional[str] = None
    job_function: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_range: Optional[str] = None
    company_rating: Optional[float] = None
    company_reviews_count: Optional[int] = None
    vacancy_count: Optional[int] = None
    work_from_home_type: Optional[str] = None
    site: Optional[str] = None

    # Enrichment fields
    key_skills: Optional[List[str]] = None
    match_score: Optional[int] = None
    match_reasons: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    resume_alignment_level: Optional[str] = None
    why_this_job_fits: Optional[str] = None

class JobResponse(BaseModel):
    jobs: List[JobPost] = []

class Site(str, Enum):
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"

class ScraperInput(BaseModel):
    site_type: List[Site]
    search_term: Optional[str] = None
    google_search_term: Optional[str] = None
    location: Optional[str] = None
    country: Country = Country.INDIA
    distance: Optional[int] = None
    is_remote: bool = False
    job_type: Optional[JobType] = None
    easy_apply: Optional[bool] = None
    offset: int = 0
    linkedin_fetch_description: bool = False
    linkedin_company_ids: Optional[List[int]] = None
    description_format: DescriptionFormat = DescriptionFormat.MARKDOWN
    results_wanted: int = 15
    hours_old: Optional[int] = None

class SalarySource(str, Enum):
    DIRECT_DATA = "direct_data"
    DESCRIPTION = "description"


class Scraper:
    """Minimal base class for scrapers. Subclasses should implement `scrape`."""
    def __init__(self, site: Site, proxies=None, ca_cert=None):
        self.site = site
        self.proxies = proxies
        self.ca_cert = ca_cert
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        raise NotImplementedError("Scrape method must be implemented by scraper subclasses.")