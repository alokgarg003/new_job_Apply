# jobspy/indeed/indeed.py
"""
Indeed scraper using public search pages (HTML + embedded JSON).
Replaces the GraphQL API with reliable scraping for India and remote fallback.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
from urllib.parse import urljoin

from jobspy.indeed.constant import headers as indeed_headers
from jobspy.indeed.util import (
    get_compensation,
    get_job_type,
    is_job_remote,
    get_compensation_interval,
)
from jobspy.model import (
    Scraper,
    ScraperInput,
    Site,
    JobPost,
    Location,
    JobResponse,
    JobType,
    DescriptionFormat,
    Country,
)
from jobspy.util import (
    extract_emails_from_text,
    markdown_converter,
    create_session,
    create_logger,
    currency_parser,
)
from jobspy.indeed.fallback import scrape_indeed_with_fallback

log = create_logger("Indeed")


class Indeed(Scraper):
    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None
    ):
        super().__init__(Site.INDEED, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=self.ca_cert,
            is_tls=True,          # verify TLS
            has_retry=True,
            delay=1,
            clear_cookies=True,
        )
        # Add retry strategy with backoff
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update(indeed_headers)
        self.scraper_input = None
        self.jobs_per_page = 100
        self.seen_urls = set()
        self.headers = indeed_headers.copy()
        self.api_country_code = None
        self.base_url = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        self.scraper_input.results_wanted = min(900, scraper_input.results_wanted)
        results_wanted = scraper_input.results_wanted

        # Select base URLs by country
        if scraper_input.country == Country.INDIA:
            india_base = "https://in.indeed.com"
            remote_base = "https://www.indeed.com"
        else:
            india_base = "https://www.indeed.com"
            remote_base = "https://www.indeed.com"

        # Build query
        search_term = scraper_input.search_term or ""
        location = scraper_input.location or "India"
        fromage = scraper_input.hours_old // 24 if scraper_input.hours_old else 3

        # Fetch jobs with India → Remote fallback
        raw_jobs = scrape_indeed_with_fallback(
            q=search_term,
            location=location,
            fromage=fromage,
            results_wanted=results_wanted + scraper_input.offset,
            headers=self.headers,
            session=self.session,
            india_base=india_base,
            remote_base=remote_base,
        )

        # Process raw jobs into JobPost
        job_list = []
        for raw in raw_jobs:
            job_post = self._process_raw_job(raw)
            if job_post:
                job_list.append(job_post)

        # Apply offset and limit
        final_jobs = job_list[scraper_input.offset: scraper_input.offset + results_wanted]
        log.info(f"Indeed: collected {len(final_jobs)} jobs after offset/limit")
        return JobResponse(jobs=final_jobs)

    def _process_raw_job(self, raw: Dict[str, Any]) -> Optional[JobPost]:
        jk = raw.get("jk")
        if not jk or jk in self.seen_urls:
            return None
        self.seen_urls.add(jk)

        title = raw.get("title", "")
        company = raw.get("company", "")
        location_str = raw.get("location", "")
        link = raw.get("link", "")
        job_url = urljoin("https://in.indeed.com", link) if link else None

        # Basic location parsing
        city = state = country = None
        if location_str and "," in location_str:
            parts = [p.strip() for p in location_str.split(",")]
            city = parts[0] if parts else None
            state = parts[1] if len(parts) > 1 else None
            country = parts[-1] if len(parts) > 2 else "India"
        else:
            city = location_str

        # Fetch description (optional, short timeout)
        description = ""
        if job_url:
            try:
                res = self.session.get(job_url, timeout=5)
                html = getattr(res, "text", "")
                description = self._clean_description(html)
            except Exception:
                pass

        # Job type, compensation from raw or description
        job_type = None
        compensation = None
        is_remote = is_job_remote({"location": location_str}, description)

        # Build JobPost
        job_post = JobPost(
            id=f"in-{jk}",
            title=title,
            company_name=company,
            location=Location(city=city, state=state, country=country),
            is_remote=is_remote,
            job_url=job_url,
            description=description,
            emails=extract_emails_from_text(description),
            job_type=job_type,
            compensation=compensation,
            date_posted=datetime.now().date(),
            job_url_direct=job_url,
        )
        return job_post

    def _clean_description(self, html: str) -> str:
        """Extract clean text from job description HTML."""
        if not html:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        return text.strip()