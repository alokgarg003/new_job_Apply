# jobspy/exception.py
from typing import Callable, Optional

class JobScrapingException(Exception):
    def __init__(self, message: str, code: str = "GEN_ERROR", resolve: Optional[Callable[[], str]] = None, retry_after: Optional[int] = None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.code = code
        self.resolve = resolve
        self.retry_after = retry_after

class PageFetchError(JobScrapingException):
    def __init__(self, url: str, status_code: int):
        msg = f"Failed to fetch {url} – Status {status_code}"
        super().__init__(msg, code=f"PAGE_{status_code}", url=url)

class ResumeParsingException(JobScrapingException):
    def __init__(self, error_msg: str, missing_sections: Optional[list[str]] = None):
        msg = f"Resume analysis failed: {error_msg}"
        sections = ", ".join(missing_sections or ["any"])
        super().__init__(msg, code="RESUME_PARSE_ERROR", missing_sections=sections)

class SiteAuthorizationError(JobScrapingException):
    def __init__(self, site: str, message: str):
        msg = f"Authorization failed for {site}"
        super().__init__(msg, code=f"AUTH_{site.upper()}", resolve=self._suggest_solution)
        self.site = site

    def _suggest_solution(self) -> str:
        return "Check proxies or request API access"

class JobURLValidationError(JobScrapingException):
    def __init__(self, url: str):
        super().__init__(f"Invalid job URL: {url}", code="INVALID_URL", url=url)

class RateLimitError(JobScrapingException):
    def __init__(self, remaining: int, headers: dict):
        msg = f"Rate limit reached. Remaining requests: {remaining}"
        super().__init__(msg, code="RATE_LIMIT", resolve=self._suggest_resolution)
        self.remaining = remaining
        self.headers = headers

    def _suggest_resolution(self) -> str:
        return "Reduce request frequency or add proxy rotation"

class APIResponseFormatError(JobScrapingException):
    def __init__(self, service: str, expected: str, received: str):
        msg = f"Unexpected response from {service}"
        super().__init__(msg, code=f"FORMAT_{service.upper()}", service=service, expected=expected, received=received)

class RecaptchaChallenge(JobScrapingException):
    def __init__(self, site: str, challenge: str):
        msg = f"CAPTCHA required for {site}"
        super().__init__(msg, code="CAPTCHA_REQ", challenge=challenge, resolve="Check rate limits or use headless browser")

class DataValidationError(Exception):
    def __str__(self):
        return f"Data validation failed: {self.errors}"

# Site‑specific aliases (backward compatibility)
class LinkedInException(JobScrapingException):
    def __init__(self, message: str):
        super().__init__(message, code="LINKEDIN_ERROR")

class NaukriException(JobScrapingException):
    def __init__(self, message: str):
        super().__init__(message, code="NAUKRI_ERROR")