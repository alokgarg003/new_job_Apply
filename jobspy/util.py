# jobspy/util.py
"""
Utility helpers shared by all scrapers.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import numpy as np
import requests
from markdownify import markdownify as md
from requests.adapters import HTTPAdapter, Retry
from urllib3.exceptions import InsecureRequestWarning

from jobspy.model import JobType, Site

# --------------------------------------------------------------------------- #
# 1️⃣  Logging helper
# --------------------------------------------------------------------------- #
def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"JobSpy:{name}")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# --------------------------------------------------------------------------- #
# 2️⃣  Session factory – TLS / proxy / retry
# --------------------------------------------------------------------------- #
class RotatingProxySession:
    def __init__(self, proxies: List[str] | str | None = None):
        if isinstance(proxies, str):
            self.proxy_cycle = iter([self._format_proxy(proxies)])
        elif isinstance(proxies, list) and proxies:
            self.proxy_cycle = iter([self._format_proxy(p) for p in proxies])
        else:
            self.proxy_cycle = None

    @staticmethod
    def _format_proxy(proxy: str) -> dict[str, str]:
        if proxy.startswith(("http://", "https://")):
            return {"http": proxy, "https": proxy}
        if proxy.startswith("socks5://"):
            return {"http": proxy, "https": proxy}
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}


class RequestsRotating(RotatingProxySession, requests.Session):
    def __init__(
        self,
        proxies: List[str] | str | None = None,
        has_retry: bool = False,
        delay: int = 1,
        clear_cookies: bool = False,
    ):
        RotatingProxySession.__init__(self, proxies=proxies)
        requests.Session.__init__(self)
        self.clear_cookies = clear_cookies
        if has_retry:
            retries = Retry(
                total=3,
                connect=3,
                status=3,
                status_forcelist=[500, 502, 503, 504, 429],
                backoff_factor=delay,
            )
            adapter = HTTPAdapter(max_retries=retries)
            self.mount("http://", adapter)
            self.mount("https://", adapter)

    def request(self, method, url, **kwargs):
        if self.clear_cookies:
            self.cookies.clear()
        if self.proxy_cycle:
            self.proxies = next(self.proxy_cycle)
        return super().request(method, url, **kwargs)


class TLSRotating(RotatingProxySession, requests.Session):
    """TLS session that accepts any cert and supports rotating proxies."""
    def __init__(self, proxies: List[str] | str | None = None):
        RotatingProxySession.__init__(self, proxies=proxies)
        requests.Session.__init__(self)

    def request(self, method, url, **kwargs):
        if self.proxy_cycle:
            self.proxies = next(self.proxy_cycle)
        return super().request(method, url, **kwargs)


def create_session(
    *,
    proxies: dict | str | None = None,
    ca_cert: str | None = None,
    is_tls: bool = True,
    has_retry: bool = False,
    delay: int = 1,
    clear_cookies: bool = False,
) -> requests.Session:
    if is_tls:
        sess = TLSRotating(proxies=proxies)
    else:
        sess = RequestsRotating(
            proxies=proxies,
            has_retry=has_retry,
            delay=delay,
            clear_cookies=clear_cookies,
        )
    if ca_cert:
        sess.verify = ca_cert
    return sess


# --------------------------------------------------------------------------- #
# 3️⃣  Misc helpers
# --------------------------------------------------------------------------- #
def extract_emails_from_text(text: str | None) -> List[str] | None:
    if not text:
        return None
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)


def get_enum_from_job_type(label: str) -> JobType | None:
    for jt in JobType:
        if label.lower() in jt.value:
            return jt
    return None


def markdown_converter(html: str | None) -> str | None:
    if not html:
        return None
    return md(html).strip()


def remove_attributes(tag):
    for attr in list(tag.attrs):
        del tag[attr]
    return tag


# --------------------------------------------------------------------------- #
# 4️⃣  Salary helpers
# --------------------------------------------------------------------------- #
def currency_parser(s: str) -> float:
    s = re.sub(r"[^0-9.,-]", "", s)
    s = re.sub(r"[.,]", "", s[:-3]) + s[-3:]
    return float(s.replace(",", ".") if "," in s else s)


def extract_salary(
    salary_str: str,
    enforce_annual: bool = False,
) -> tuple[Optional[str], Optional[float], Optional[float], Optional[str]]:
    if not salary_str:
        return None, None, None, None
    match = re.search(
        r"\$(?P<min>[\d,.]+)\s*(-|—|to)\s*\$(?P<max>[\d,.]+)", salary_str, re.I
    )
    if not match:
        return None, None, None, None
    min_amt = currency_parser(match.group("min"))
    max_amt = currency_parser(match.group("max"))
    interval = (
        "hourly" if min_amt < 350 else "monthly" if min_amt < 30000 else "yearly"
    )
    if enforce_annual:
        if interval == "hourly":
            min_amt *= 2080
            max_amt *= 2080
        elif interval == "monthly":
            min_amt *= 12
            max_amt *= 12
        interval = "yearly"
    return interval, min_amt, max_amt, "USD"


def extract_job_type(description: str):
    if not description:
        return []
    keywords = {
        JobType.FULL_TIME: r"full\s?time",
        JobType.PART_TIME: r"part\s?time",
        JobType.INTERNSHIP: r"internship",
        JobType.CONTRACT: r"contract",
    }
    listing_types = []
    for key, pattern in keywords.items():
        if re.search(pattern, description, re.IGNORECASE):
            listing_types.append(key)
    return listing_types if listing_types else None


def map_str_to_site(site_name: str):
    if not site_name:
        raise ValueError("Empty site name")
    name = site_name.strip().upper().replace("-", "_").replace(" ", "_")
    if name == "ZIPRECRUITER":
        name = "ZIP_RECRUITER"
    try:
        return Site[name]
    except KeyError:
        raise ValueError(f"Unknown site: {site_name}. Valid sites: {[s.value for s in Site]}")


def get_enum_from_value(value_str):
    for job_type in JobType:
        if value_str in job_type.value:
            return job_type
    raise Exception(f"Invalid job type: {value_str}")


def convert_to_annual(job_data: dict):
    if job_data["interval"] == "hourly":
        job_data["min_amount"] *= 2080
        job_data["max_amount"] *= 2080
    if job_data["interval"] == "monthly":
        job_data["min_amount"] *= 12
        job_data["max_amount"] *= 12
    if job_data["interval"] == "weekly":
        job_data["min_amount"] *= 52
        job_data["max_amount"] *= 52
    if job_data["interval"] == "daily":
        job_data["min_amount"] *= 260
        job_data["max_amount"] *= 260
    job_data["interval"] = "yearly"


# --------------------------------------------------------------------------- #
# 5️⃣  Text normalization (used by ProfileMatchEvaluator)
# --------------------------------------------------------------------------- #
def norm_text(text: str) -> str:
    """Normalize text to lowercase for case‑insensitive matching."""
    if not text:
        return ""
    return text.lower()


# --------------------------------------------------------------------------- #
# 6️⃣  Desired output column order
# --------------------------------------------------------------------------- #
desired_order = [
    "id", "site", "job_url", "job_url_direct", "title", "company", "location",
    "date_posted", "job_type", "salary_source", "interval", "min_amount", "max_amount",
    "currency", "is_remote", "job_level", "job_function", "listing_type", "emails",
    "description", "company_industry", "company_url", "company_logo",
    "company_url_direct", "company_addresses", "company_num_employees",
    "company_revenue", "company_description", "skills", "experience_range",
    "company_rating", "company_reviews_count", "vacancy_count", "work_from_home_type",
]