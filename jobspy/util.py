# jobspy/util.py
from __future__ import annotations
import logging
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from typing import List, Optional
from enum import Enum
import re

def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"JobSpy:{name}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

class SessionFactory:
    def __init__(self, proxies=None, ca_cert=None, is_tls=True, has_retry=False, delay=1, clear_cookies=False):
        self.proxies = proxies
        self.ca_cert = ca_cert
        self.is_tls = is_tls
        self.has_retry = has_retry
        self.delay = delay
        self.clear_cookies = clear_cookies

    def make(self) -> requests.Session:
        if self.is_tls:
            sess = requests.Session()
            if self.ca_cert:
                sess.verify = self.ca_cert
        else:
            sess = requests.Session()
            if self.ca_cert:
                sess.verify = self.ca_cert
        if self.clear_cookies:
            sess.cookies.clear()
        if self.proxies:
            sess.proxies.update(self.proxies)
        if self.has_retry:
            retries = Retry(
                total=3,
                connect=3,
                status=3,
                status_forcelist=[500, 502, 503, 504, 429],
                backoff_factor=self.delay,
            )
            adapter = HTTPAdapter(max_retries=retries)
            sess.mount("http://", adapter)
            sess.mount("https://", adapter)
        return sess

def extract_emails_from_text(text: str | None) -> List[str] | None:
    if not text: return None
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)

def currency_parser(s: str) -> float:
    s = re.sub(r"[^0-9.,-]", "", s)
    s = re.sub(r"[.,]", "", s[:-3]) + s[-3:]
    return float(s.replace(",", "."))

def extract_salary(salary_str: str, enforce_annual: bool = False) -> tuple[Optional[str], Optional[float], Optional[float], Optional[str]]:
    if not salary_str: return None, None, None, None
    match = re.search(r"\$(?P<min>[\d,.]+)\s*(-|—|to)\s*\$(?P<max>[\d,.]+)", salary_str, re.I)
    if not match: return None, None, None, None
    min_amt = currency_parser(match.group("min"))
    max_amt = currency_parser(match.group("max"))
    interval = "hourly" if min_amt < 350 else "monthly" if min_amt < 30000 else "yearly"
    if enforce_annual:
        if interval == "hourly": min_amt, max_amt = min_amt * 2080, max_amt * 2080
        elif interval == "monthly": min_amt, max_amt = min_amt * 12, max_amt * 12
        interval = "yearly"
    return interval, min_amt, max_amt, "USD"

def map_str_to_site(site_name: str):
    if not site_name: raise ValueError("Empty site name")
    name = site_name.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        from jobspy.model import Site
        return Site[name]
    except KeyError:
        raise ValueError(f"Unknown site: {site_name}. Valid: {[s.value for s in Site]}")

def norm_text(text: str) -> str:
    if not text: return ""
    return text.lower()


def create_session(proxies=None, ca_cert=None, is_tls=True, has_retry=False, delay=1, clear_cookies=False):
    """Create and return a configured requests session."""
    return SessionFactory(proxies=proxies, ca_cert=ca_cert, is_tls=is_tls, has_retry=has_retry, delay=delay, clear_cookies=clear_cookies).make()


def remove_attributes(tag):
    """Remove attributes from a BeautifulSoup Tag (recursively) to sanitize HTML."""
    try:
        if hasattr(tag, "attrs"):
            tag.attrs = {}
        for child in tag.find_all(True):
            child.attrs = {}
    except Exception:
        pass
    return tag


def markdown_converter(html: str) -> str:
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    remove_attributes(soup)
    # Use markdownify to convert HTML to Markdown
    try:
        return md(str(soup))
    except Exception:
        return str(soup)


def get_enum_from_job_type(value_str):
    from jobspy.model import JobType
    if not value_str: return None
    val = value_str.lower()
    for job_type in JobType:
        if val in job_type.value:
            return job_type
    raise Exception(f"Invalid job type: {value_str}")


def get_enum_from_value(enum_cls, value):
    """Generic helper to get an enum member from a string value or name.

    Returns the matched enum member or raises ValueError if not found.
    """
    if value is None:
        return None
    val = str(value).strip().lower()
    for member in enum_cls:
        if val == member.value or val == member.name.lower():
            return member
    raise ValueError(f"{value} is not a valid member of {enum_cls}")


def extract_job_type(job_type_input):
    """Normalize various job type inputs into a list of `JobType` enums or None."""
    if not job_type_input:
        return None
    from jobspy.model import JobType
    # If it's already a JobType, return as list
    if isinstance(job_type_input, JobType):
        return [job_type_input]
    # If input is list-like, map each
    if isinstance(job_type_input, (list, tuple, set)):
        res = []
        for v in job_type_input:
            if isinstance(v, JobType):
                res.append(v)
            else:
                res.append(get_enum_from_job_type(str(v)))
        return res
    # Single string
    return [get_enum_from_job_type(str(job_type_input))]


def convert_to_annual(job_data: dict):
    """Convert intervals on a scraped job_data dict to yearly amounts in-place."""
    if not job_data or "interval" not in job_data:
        return
    iv = job_data.get("interval")
    if iv == "hourly":
        if job_data.get("min_amount"): job_data["min_amount"] *= 2080
        if job_data.get("max_amount"): job_data["max_amount"] *= 2080
    elif iv == "monthly":
        if job_data.get("min_amount"): job_data["min_amount"] *= 12
        if job_data.get("max_amount"): job_data["max_amount"] *= 12
    elif iv == "weekly":
        if job_data.get("min_amount"): job_data["min_amount"] *= 52
        if job_data.get("max_amount"): job_data["max_amount"] *= 52
    elif iv == "daily":
        if job_data.get("min_amount"): job_data["min_amount"] *= 260
        if job_data.get("max_amount"): job_data["max_amount"] *= 260
    job_data["interval"] = "yearly"


# Desired CSV output order (used by `scrape_jobs`) - kept here to be exported from `jobspy.util`
desired_order = [
    "id", "site", "job_url", "job_url_direct", "title", "company", "location",
    "date_posted", "job_type", "salary_source", "interval", "min_amount", "max_amount",
    "currency", "is_remote", "job_level", "job_function", "listing_type", "emails",
    "description", "company_industry", "company_url", "company_logo",
    "company_url_direct", "company_addresses", "company_num_employees",
    "company_revenue", "company_description", "skills", "experience_range",
    "company_rating", "company_reviews_count", "vacancy_count", "work_from_home_type",
]