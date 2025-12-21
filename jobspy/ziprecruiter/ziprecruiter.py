# jobspy/ziprecruiter/ziprecruiter.py
"""
ZipRecruiter scraper using the job listings API.
"""

from __future__ import annotations

import math
import random
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse, unquote

import regex as re
from bs4 import BeautifulSoup
from bs4.element import Tag

from jobspy.exception import ZipRecruiterException
from jobspy.ziprecruiter.constant import headers
from jobspy.ziprecruiter.util import (
    is_job_remote,
    job_type_code,
    parse_job_type,
    parse_job_level,
    parse_company_industry,
)
from jobspy.model import (
    JobPost,
    Location,
    JobResponse,
    Country,
    Compensation,
    DescriptionFormat,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy.util import (
    extract_emails_from_text,
    currency_parser,
    markdown_converter,
    create_session,
    remove_attributes,
    create_logger,
)

log = create_logger("ZipRecruiter")

class ZipRecruiter(Scraper):
    base_url = "https://www.ziprecruiter.com"
    delay = 3
    band_delay = 4
    jobs_per_page = 20

    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None
    ):
        super().__init__(Site.ZIP_RECRUITER, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=self.ca_cert,
            is_tls=False,
            has_retry=True,
            delay=5,
            clear_cookies=True,
        )
        self.session.headers.update(headers)
        self.scraper_input = None
        self.country = "us"
        self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        start = scraper_input.offset // 10 * 10 if scraper_input.offset else 0
        request_count = 0
        seconds_old = (
            scraper_input.hours_old * 3600 if scraper_input.hours_old else None
        )
        continue_search = (
            lambda: len(job_list) < scraper_input.results_wanted and start < 1000
        )
        while continue_search():
            request_count += 1
            log.info(
                f"search page: {request_count} / {math.ceil(scraper_input.results_wanted / 10)}"
            )
            params = {
                "q": scraper_input.search_term,
                "location": scraper_input.location,
                "search_type": "jobs",
                "page": start,
                "remote": "true" if scraper_input.is_remote else None,
            }
            if seconds_old is not None:
                params["date_posted"] = seconds_old

            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = self.session.get(
                    f"{self.base_url}/jobs",
                    params=params,
                    timeout=10,
                )
                if response.status_code not in range(200, 400):
                    if response.status_code == 429:
                        err = f"429 Response - Blocked by ZipRecruiter for too many requests"
                    else:
                        err = f"ZipRecruiter response status code {response.status_code}"
                        err += f" - {response.text}"
                    log.error(err)
                    return JobResponse(jobs=job_list)
            except Exception as e:
                if "Proxy responded with" in str(e):
                    log.error(f"ZipRecruiter: Bad proxy")
                else:
                    log.error(f"ZipRecruiter: {str(e)}")
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="job-listing")
            if len(job_cards) == 0:
                return JobResponse(jobs=job_list)

            for job_card in job_cards:
                href_tag = job_card.find("a", class_="job-title")
                if href_tag and "href" in href_tag.attrs:
                    href = href_tag["href"]
                    job_id = href.split("/")[-1]

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    try:
                        fetch_desc = scraper_input.linkedin_fetch_description
                        job_post = self._process_job(job_card, job_id, fetch_desc)
                        if job_post:
                            job_list.append(job_post)
                        if not continue_search():
                            break
                    except Exception as e:
                        raise ZipRecruiterException(str(e))

            if continue_search():
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                start += len(job_list)

        job_list = job_list[: scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_job(
        self, job_card: Tag, job_id: str, full_descr: bool
    ) -> Optional[JobPost]:
        salary_tag = job_card.find("span", class_="job-salary")
        compensation = None
        if salary_tag:
            salary_text = salary_tag.get_text(separator=" ").strip()
            salary_values = [currency_parser(value) for value in salary_text.split("-")]
            salary_min = salary_values[0]
            salary_max = salary_values[1]
            currency = salary_text[0] if salary_text[0] != "$" else "USD"
            compensation = Compensation(
                min_amount=int(salary_min),
                max_amount=int(salary_max),
                currency=currency,
            )

        title_tag = job_card.find("h2", class_="job-title")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        company_tag = job_card.find("div", class_="company-name")
        company = company_tag.get_text(strip=True) if company_tag else "N/A"

        metadata_card = job_card.find("div", class_="job-metadata")
        location = self._get_location(metadata_card)

        datetime_tag = (
            metadata_card.find("time", class_="job-posted")
            if metadata_card
            else None
        )
        date_posted = None
        if datetime_tag and "datetime" in datetime_tag.attrs:
            datetime_str = datetime_tag["datetime"]
            try:
                date_posted = datetime.strptime(datetime_str, "%Y-%m-%d")
            except:
                date_posted = None

        job_details = {}
        if full_descr:
            job_details = self._get_job_details(job_id)
            description = job_details.get("description")
        else:
            description = None

        is_remote = is_job_remote(title, description, location)

        return JobPost(
            id=f"zr-{job_id}",
            title=title,
            company_name=company,
            location=location,
            is_remote=is_remote,
            date_posted=date_posted,
            job_url=f"{self.base_url}/jobs/{job_id}",
            compensation=compensation,
            job_type=job_details.get("job_type"),
            job_level=job_details.get("job_level", "").lower(),
            company_industry=job_details.get("company_industry"),
            description=description,
            job_url_direct=job_details.get("job_url_direct"),
            emails=extract_emails_from_text(description),
            company_logo=job_details.get("company_logo"),
            job_function=job_details.get("job_function"),
        )

    def _get_job_details(self, job_id: str) -> dict:
        try:
            response = self.session.get(
                f"{self.base_url}/jobs/{job_id}", timeout=5
            )
            response.raise_for_status()
        except:
            return {}
        if "ziprecruiter.com/signup" in response.url:
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        div_content = soup.find(
            "div", class_=lambda x: x and "job-description" in x
        )
        description = None
        if div_content is not None:
            div_content = remove_attributes(div_content)
            description = div_content.prettify(formatter="html")
            if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)

        h3_tag = soup.find(
            "h3", text=lambda text: text and "Job function" in text.strip()
        )
        job_function = None
        if h3_tag:
            job_function_span = h3_tag.find_next(
                "span", class_="job-criteria-text"
            )
            if job_function_span:
                job_function = job_function_span.text.strip()

        company_logo = (
            logo_image.get("data-delayed-url")
            if (logo_image := soup.find("img", {"class": "company-logo"}))
            else None
        )
        return {
            "description": description,
            "job_level": parse_job_level(soup),
            "company_industry": parse_company_industry(soup),
            "job_type": parse_job_type(soup),
            "job_url_direct": self._parse_job_url_direct(soup),
            "company_logo": company_logo,
            "job_function": job_function,
        }

    def _get_location(self, metadata_card: Optional[Tag]) -> Location:
        location = Location(country=Country.from_string(self.country))
        if metadata_card is not None:
            location_tag = metadata_card.find("span", class_="job-location")
            location_string = location_tag.text.strip() if location_tag else "N/A"
            parts = location_string.split(", ")
            if len(parts) == 2:
                city, state = parts
                location = Location(
                    city=city,
                    state=state,
                    country=Country.from_string(self.country),
                )
            elif len(parts) == 3:
                city, state, country = parts
                country = Country.from_string(country)
                location = Location(city=city, state=state, country=country)
        return location

    def _parse_job_url_direct(self, soup: BeautifulSoup) -> str | None:
        job_url_direct = None
        job_url_direct_content = soup.find("a", {"id": "apply-now"})
        if job_url_direct_content:
            job_url_direct = job_url_direct_content.get("href")
        return job_url_direct