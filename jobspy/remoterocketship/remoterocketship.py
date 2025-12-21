# jobspy/remoterocketship/remoterocketship.py
"""
RemoteRocketship scraper.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Tuple

from bs4 import BeautifulSoup

from jobspy.remoterocketship.constant import headers
from jobspy.remoterocketship.util import extract_remote_info
from jobspy.model import (
    Scraper,
    ScraperInput,
    Site,
    JobPost,
    JobResponse,
    Location,
    JobType,
    DescriptionFormat,
)
from jobspy.util import (
    extract_emails_from_text,
    markdown_converter,
    create_session,
    create_logger,
)
from jobspy.exception import JobScrapingException

log = create_logger("RemoteRocketship")

class RemoteRocketship(Scraper):
    base_url = "https://www.remoterocketship.com"
    delay = 3
    band_delay = 4

    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None
    ):
        super().__init__(Site.REMOTE_ROCKETSHIP, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, is_tls=True, has_retry=True
        )
        self.session.headers.update(headers)
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        self.scraper_input.results_wanted = min(900, scraper_input.results_wanted)
        job_list: list[JobPost] = []
        seen_ids = set()
        page = 1

        while len(job_list) < scraper_input.results_wanted:
            log.info(f"search page: {page}")
            params = {
                "page": page,
                "sort": "DateAdded",
                "jobTitle": scraper_input.search_term,
                "q": scraper_input.search_term,
            }
            response = self.session.get(f"{self.base_url}/", params=params, timeout=15)
            if response.status_code != 200:
                log.error(f"RemoteRocketship responded with status {response.status_code}")
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="job-card")
            if not job_cards:
                break

            for card in job_cards:
                job_url = card.find("a", class_="job-card-link")
                if not job_url or "href" not in job_url.attrs:
                    continue
                job_url = job_url["href"]
                job_id = job_url.split("/")[-1]

                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                try:
                    job_post = self._process_job(card, job_url)
                    if job_post:
                        job_list.append(job_post)
                    if len(job_list) >= scraper_input.results_wanted:
                        break
                except Exception as e:
                    log.error(f"Error processing job {job_id}: {str(e)}")

            page += 1
            time.sleep(random.uniform(self.delay, self.delay + self.band_delay))

        return JobResponse(jobs=job_list[:scraper_input.results_wanted])

    def _process_job(self, card: BeautifulSoup, job_url: str) -> JobPost | None:
        title = card.find("h2", class_="job-title")
        title = title.get_text(strip=True) if title else "N/A"

        company = card.find("div", class_="company-name")
        company = company.get_text(strip=True) if company else "N/A"

        location = card.find("div", class_="job-location")
        location = location.get_text(strip=True) if location else "Remote"

        date_posted = None
        date_tag = card.find("div", class_="job-date")
        if date_tag:
            date_str = date_tag.get_text(strip=True)
            try:
                date_posted = datetime.strptime(date_str, "%b %d, %Y").date()
            except:
                pass

        description = card.find("div", class_="job-description")
        description = description.get_text(strip=True) if description else ""
        if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
            description = markdown_converter(description)

        return JobPost(
            id=f"rr-{job_url.split('/')[-1]}",
            title=title,
            company_name=company,
            location=Location(city=location, country="Remote"),
            is_remote=True,
            date_posted=date_posted,
            job_url=f"{self.base_url}{job_url}",
            description=description,
            emails=extract_emails_from_text(description),
            job_type=None,  # RemoteRocketship does not expose job type clearly
        )