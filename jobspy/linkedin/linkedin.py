# jobspy/linkedin/linkedin.py
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
from jobspy.model import (
    JobPost, Location, JobResponse, Country, Compensation, DescriptionFormat,
    Scraper, ScraperInput, Site,
)
from jobspy.util import (
    extract_emails_from_text, currency_parser, markdown_converter,
    create_session, remove_attributes, create_logger,
)
from jobspy.linkedin.util import is_job_remote, job_type_code, parse_job_type, parse_job_level, parse_company_industry
import settings

log = create_logger("LinkedIn")

class LinkedIn(Scraper):
    base_url = "https://www.linkedin.com"
    delay = settings.LI_DELAY
    band_delay = settings.LI_BAND_DELAY
    jobs_per_page = settings.LI_JOBS_PER_PAGE
    max_pages = settings.LI_MAX_PAGES

    def __init__(self, proxies=None, ca_cert=None):
        super().__init__(Site.LINKEDIN, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=self.ca_cert,
            is_tls=False,
            has_retry=True,
            delay=self.delay,
            clear_cookies=True,
        )
        self.headers = {
            "authority": "www.linkedin.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.session.headers.update(self.headers)
        self.scraper_input = None
        self.country = "worldwide"
        self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        start = (scraper_input.offset // 10) * 10 if scraper_input.offset else 0
        request_count = 0
        seconds_old = scraper_input.hours_old * 3600 if scraper_input.hours_old else None
        continue_search = lambda: len(job_list) < scraper_input.results_wanted and start < 1000
        while continue_search():
            request_count += 1
            log.info(f"LinkedIn page {request_count} / {math.ceil(scraper_input.results_wanted / 10)}")
            params = {
                "keywords": scraper_input.search_term,
                "location": scraper_input.location,
                "distance": scraper_input.distance,
                "f_WT": 2 if scraper_input.is_remote else None,
                "f_JT": job_type_code(scraper_input.job_type) if scraper_input.job_type else None,
                "pageNum": 0,
                "start": start,
                "f_AL": "true" if scraper_input.easy_apply else None,
                "f_C": ",".join(map(str, scraper_input.linkedin_company_ids)) if scraper_input.linkedin_company_ids else None,
            }
            if seconds_old is not None:
                params["f_TPR"] = f"r{seconds_old}"
            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = self.session.get(
                    f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?",
                    params=params,
                    timeout=10,
                )
                if response.status_code not in range(200, 400):
                    if response.status_code == 429:
                        err = "429 Response - Blocked by LinkedIn for too many requests"
                    else:
                        err = f"LinkedIn response status code {response.status_code}"
                    log.error(err)
                    return JobResponse(jobs=job_list)
            except Exception as e:
                log.error(f"LinkedIn request failed: {str(e)}")
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="base-search-card")
            if not job_cards:
                return JobResponse(jobs=job_list)

            for job_card in job_cards:
                href_tag = job_card.find("a", class_="base-card__full-link")
                if href_tag and "href" in href_tag.attrs:
                    href = href_tag.attrs["href"].split("?")[0]
                    job_id = href.split("-")[-1]
                    if job_id in seen_ids: continue
                    seen_ids.add(job_id)
                    try:
                        job_post = self._process_job(job_card, job_id, scraper_input.linkedin_fetch_description)
                        if job_post: job_list.append(job_post)
                        if not continue_search(): break
                    except Exception as e:
                        raise LinkedInException(str(e))
            if continue_search():
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                start += len(job_list)
        job_list = job_list[:scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_job(self, job_card: Tag, job_id: str, full_descr: bool) -> Optional[JobPost]:
        salary_tag = job_card.find("span", class_="job-search-card__salary-info")
        compensation = None
        if salary_tag:
            salary_text = salary_tag.get_text(separator=" ").strip()
            salary_values = [currency_parser(v) for v in salary_text.split("-")]
            salary_min, salary_max = salary_values[0], salary_values[1]
            currency = salary_text[0] if salary_text[0] != "$" else "USD"
            compensation = Compensation(min_amount=int(salary_min), max_amount=int(salary_max), currency=currency)

        title_tag = job_card.find("span", class_="sr-only")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        company_tag = job_card.find("h4", class_="base-search-card__subtitle")
        company_a_tag = company_tag.find("a") if company_tag else None
        company_url = (
            f"{self.base_url}" + urlunparse(urlparse(company_a_tag.get("href"))._replace(query=""))
            if company_a_tag and company_a_tag.has_attr("href")
            else ""
        )
        company = company_a_tag.get_text(strip=True) if company_a_tag else "N/A"

        metadata_card = job_card.find("div", class_="base-search-card__metadata")
        location = self._get_location(metadata_card)

        datetime_tag = metadata_card.find("time", class_="job-search-card__listdate") if metadata_card else None
        date_posted = None
        if datetime_tag and "datetime" in datetime_tag.attrs:
            datetime_str = datetime_tag["datetime"]
            try:
                date_posted = datetime.strptime(datetime_str, "%Y-%m-%d").date()
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
            id=f"li-{job_id}",
            title=title,
            company_name=company,
            company_url=company_url,
            location=location,
            is_remote=is_remote,
            date_posted=date_posted,
            job_url=f"{self.base_url}/jobs/view/{job_id}",
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
            response = self.session.get(f"{self.base_url}/jobs/view/{job_id}", timeout=5)
            response.raise_for_status()
        except:
            return {}
        if "linkedin.com/signup" in response.url:
            return {}
        soup = BeautifulSoup(response.text, "html.parser")
        div_content = soup.find("div", class_=lambda x: x and "show-more-less-html__markup" in x)
        description = None
        if div_content is not None:
            div_content = remove_attributes(div_content)
            description = div_content.prettify(formatter="html")
            if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
        h3_tag = soup.find("h3", text=lambda text: text and "Job function" in text.strip())
        job_function = h3_tag.find_next("span", class_="description__job-criteria-text").get_text(strip=True) if h3_tag else None
        company_logo = soup.find("img", {"class": "artdeco-entity-image"}).get("data-delayed-url") if soup.find("img", {"class": "artdeco-entity-image"}) else None
        return {
            "description": description,
            "job_level": parse_job_level(soup),
            "company_industry": parse_company_industry(soup),
            "job_type": parse_job_type(soup),
            "job_url_direct": self._parse_job_url_direct(soup),
            "company_logo": company_logo,
            "job_function": job_function,
        }

    def _get_location(self, metadata_card) -> Location:
        location = Location(country=Country.from_string(self.country))
        if metadata_card is not None:
            location_tag = metadata_card.find("span", class_="job-search-card__location")
            location_string = location_tag.text.strip() if location_tag else "N/A"
            parts = location_string.split(", ")
            if len(parts) == 2:
                city, state = parts
                location = Location(city=city, state=state, country=Country.from_string(self.country))
            elif len(parts) == 3:
                city, state, country = parts
                country = Country.from_string(country)
                location = Location(city=city, state=state, country=country)
        return location

    def _parse_job_url_direct(self, soup: BeautifulSoup) -> str | None:
        job_url_direct = None
        code = soup.find("code", id="applyUrl")
        if code:
            m = self.job_url_direct_regex.search(code.decode_contents().strip())
            if m: job_url_direct = unquote(m.group())
        return job_url_direct

# jobspy/linkedin/exception.py
from jobspy.exception import LinkedInException

# jobspy/linkedin/util.py
from bs4 import BeautifulSoup
from jobspy.model import JobType, Location
from jobspy.util import get_enum_from_job_type

def job_type_code(job_type_enum) -> str:
    return {
        JobType.FULL_TIME: "F",
        JobType.PART_TIME: "P",
        JobType.INTERNSHIP: "I",
        JobType.CONTRACT: "C",
        JobType.TEMPORARY: "T",
    }.get(job_type_enum, "")

def parse_job_type(soup) -> list[JobType] | None:
    h3 = soup.find("h3", class_="description__job-criteria-subheader", string=lambda t: "Employment type" in t)
    if h3:
        span = h3.find_next_sibling("span", class_="description__job-criteria-text description__job-criteria-text--criteria")
        if span:
            val = span.get_text(strip=True).lower().replace("-", "")
            return [get_enum_from_job_type(val)] if val else []
    return []

def parse_job_level(soup) -> str | None:
    h3 = soup.find("h3", class_="description__job-criteria-subheader", string=lambda t: "Seniority level" in t)
    if h3:
        span = h3.find_next_sibling("span", class_="description__job-criteria-text description__job-criteria-text--criteria")
        return span.get_text(strip=True) if span else None
    return None

def parse_company_industry(soup) -> str | None:
    h3 = soup.find("h3", class_="description__job-criteria-subheader", string=lambda t: "Industries" in t)
    if h3:
        span = h3.find_next_sibling("span", class_="description__job-criteria-text description__job-criteria-text--criteria")
        return span.get_text(strip=True) if span else None
    return None

def is_job_remote(title, description, location) -> bool:
    remote_keywords = ["remote", "work from home", "wfh"]
    loc_str = location.display_location()
    full = f"{title} {description} {loc_str}".lower()
    return any(k in full for k in remote_keywords)