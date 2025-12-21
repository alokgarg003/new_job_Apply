# jobspy/__init__.py
"""
Top‑level hook for the JobSpy package.
Re‑exports the public classes so you can write:
    from jobspy import ScraperInput, JobPost, Site, run_personalized_pipeline, scrape_jobs
"""

from .model import (
    JobType,
    Location,
    Compensation,
    CompensationInterval,
    DescriptionFormat,
    Site,
    Scraper,
    ScraperInput,
    JobResponse,
    SalarySource,
    Country,
    JobPost,
)
from .google import Google
from .indeed import Indeed
from .linkedin import LinkedIn
from .naukri import Naukri
from .ziprecruiter import ZipRecruiter
from .glassdoor import Glassdoor
from .remoterocketship import RemoteRocketship
from .exception import (
    JobScrapingException,
    PageFetchError,
    ResumeParsingException,
    SiteAuthorizationError,
    JobURLValidationError,
    RateLimitError,
    APIResponseFormatError,
    RecaptchaChallenge,
    LinkedInException,
    IndeedException,
    NaukriException,
    ZipRecruiterException,
    GlassdoorException,
)
from .util import (
    extract_emails_from_text,
    currency_parser,
    markdown_converter,
    create_session,
    create_logger,
    remove_attributes,
    extract_salary,
    extract_job_type,
    map_str_to_site,
    get_enum_from_value,
    convert_to_annual,
    norm_text,
    desired_order,
)
from .scrape_jobs import scrape_jobs, set_logger_level
from .pipeline import run_personalized_pipeline

__all__ = [
    "ScraperInput",
    "JobPost",
    "JobResponse",
    "Site",
    "Country",
    "JobType",
    "Compensation",
    "CompensationInterval",
    "DescriptionFormat",
    "SalarySource",
    "GlassdoorException",
    "LinkedInException",
    "IndeedException",
    "NaukriException",
    "ZipRecruiterException",
    "JobScrapingException",
    "PageFetchError",
    "ResumeParsingException",
    "SiteAuthorizationError",
    "JobURLValidationError",
    "RateLimitError",
    "APIResponseFormatError",
    "RecaptchaChallenge",
    "run_personalized_pipeline",
    "scrape_jobs",
]