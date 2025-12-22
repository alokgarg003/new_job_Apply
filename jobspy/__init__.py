"""
Top‑level hook for the JobSpy package.
Re‑exports the public classes and functions for convenient access.
"""

# Import core data models and enums
from .model import (
    ScraperInput,
    JobPost,
    JobResponse,
    Site,
    Country,
    JobType,
    Compensation,
    CompensationInterval,
    DescriptionFormat,
    SalarySource,
    Location,
)
# Import the working scrapers
from .linkedin import LinkedIn
from .naukri import Naukri

# Import shared exceptions
from .exception import (
    JobScrapingException,
    LinkedInException,
    NaukriException,
    PageFetchError,
    RateLimitError,
    ResumeParsingException,
    SiteAuthorizationError,
    JobURLValidationError,
    APIResponseFormatError,
    RecaptchaChallenge,
)

# Import utility and public API functions
from .util import (
    convert_to_annual,
    create_logger,
    create_session,
    currency_parser,
    desired_order,
    extract_emails_from_text,
    extract_job_type,
    extract_salary,
    get_enum_from_value,
    markdown_converter,
    map_str_to_site,
    norm_text,
    remove_attributes,
)
from .scrape_jobs import scrape_jobs, set_logger_level
from .pipeline import run_personalized_pipeline

__all__ = [
    # Core Models
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
    # Scrapers
    "LinkedIn",
    "Naukri",
    # Exceptions (filtered to be relevant)
    "JobScrapingException",
    "LinkedInException",
    "NaukriException",
    "PageFetchError",
    "RateLimitError",
    "ResumeParsingException",
    "SiteAuthorizationError",
    "JobURLValidationError",
    "APIResponseFormatError",
    "RecaptchaChallenge",
    # Public API Functions
    "run_personalized_pipeline",
    "scrape_jobs",
]