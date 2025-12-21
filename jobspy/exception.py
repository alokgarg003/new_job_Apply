# jobspy/exception.py
"""
Custom exceptions used throughout the job scrapers.
"""

from typing import Dict, List, Any, Optional, Callable
from pydantic import ValidationError


class JobScrapingException(Exception):
    """Base exception for job scraping errors"""
    def __init__(
        self,
        message: str,
        code: str = "GEN_ERROR",
        resolve: Optional[Callable[[], str]] = None,
        retry_after: Optional[int] = None,
        *args,
        **kwargs
    ):
        super().__init__(message, *args, **kwargs)
        self.code = code
        self.resolve = resolve
        self.retry_after = retry_after


class PageFetchError(JobScrapingException):
    """Error during page fetching – may be retryable"""
    def __init__(self, url: str, status_code: int):
        msg = f"Failed to fetch {url} – Status {status_code}"
        super().__init__(msg, code=f"PAGE_{status_code}", url=url)
        self.url = url
        self.status_code = status_code


class ResumeParsingException(JobScrapingException):
    """Error handling resume analysis failures"""
    def __init__(self, error_msg: str, missing_sections: Optional[List[str]] = None):
        msg = f"Resume analysis failed: {error_msg}"
        sections = ", ".join(missing_sections or ["any"])
        super().__init__(msg, code="RESUME_PARSE_ERROR", missing_sections=sections)


class SiteAuthorizationError(JobScrapingException):
    """Error related to site access authentication"""
    def __init__(self, site: str, message: str):
        msg = f"Authorization failed for {site}"
        super().__init__(msg, code=f"AUTH_{site.upper()}", resolve=self._suggest_solution)
        self.site = site

    def _suggest_solution(self) -> str:
        return "Check proxies or request API access"


class JobURLValidationError(JobScrapingException):
    """Error when job URL is invalid or malformed"""
    def __init__(self, url: str):
        super().__init__(f"Invalid job URL: {url}", code="INVALID_URL", url=url)


class RateLimitError(JobScrapingException):
    """Error for handling rate limits and throttling"""
    def __init__(self, remaining: int, headers: dict):
        msg = f"Rate limit reached. Remaining requests: {remaining}"
        super().__init__(msg, code="RATE_LIMIT", resolve=self._suggest_resolution)
        self.remaining = remaining
        self.headers = headers

    def _suggest_resolution(self) -> str:
        return "Reduce request frequency or add proxy rotation"


class APIResponseFormatError(JobScrapingException):
    """Unexpected response structure from API"""
    def __init__(self, service: str, expected: str, received: str):
        msg = f"Unexpected response from {service}"
        super().__init__(msg, code=f"FORMAT_{service.upper()}", service=service,
                         expected=expected, received=received)


class RecaptchaChallenge(JobScrapingException):
    """Captcha/detection challenge detected"""
    def __init__(self, site: str, challenge: str):
        msg = f"CAPTCHA required for {site}"
        super().__init__(msg, code="CAPTCHA_REQ", challenge=challenge,
                         resolve="Check rate limits or use headless browser")


class DataValidationError(ValidationError):
    """Pydantic validation error handler"""
    def __str__(self):
        return f"Data validation failed: {self.errors}"


# Site‑specific exceptions for backward compatibility
class LinkedInException(JobScrapingException):
    """Error specific to LinkedIn scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="LINKEDIN_ERROR")


class IndeedException(JobScrapingException):
    """Error specific to Indeed scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="INDEED_ERROR")


class ZipRecruiterException(JobScrapingException):
    """Error specific to ZipRecruiter scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="ZIPRECRUITER_ERROR")


class GlassdoorException(JobScrapingException):
    """Error specific to Glassdoor scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="GLASSDOOR_ERROR")


class GoogleJobsException(JobScrapingException):
    """Error specific to Google Jobs scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="GOOGLE_JOBS_ERROR")


class NaukriException(JobScrapingException):
    """Error specific to Naukri scraping"""
    def __init__(self, message: str):
        super().__init__(message, code="NAUKRI_ERROR")


__all__ = [
    "JobScrapingException",
    "PageFetchError",
    "ResumeParsingException",
    "SiteAuthorizationError",
    "JobURLValidationError",
    "RateLimitError",
    "APIResponseFormatError",
    "RecaptchaChallenge",
    "DataValidationError",
    "LinkedInException",
    "IndeedException",
    "ZipRecruiterException",
    "GlassdoorException",
    "GoogleJobsException",
    "NaukriException",
]