# jobspy/naukri/naukri.py
from __future__ import annotations
import math
import random
import time
from datetime import datetime, date, timedelta
from typing import Optional
import regex as re

from jobspy.model import (
    JobPost, Location, JobResponse, Country, Compensation, DescriptionFormat,
    Scraper, ScraperInput, Site,
)
from jobspy.util import (
    extract_emails_from_text, currency_parser, markdown_converter,
    create_session, create_logger,
)
from jobspy.naukri.util import is_job_remote, parse_job_type, parse_company_industry
import settings

log = create_logger("Naukri")

class Naukri(Scraper):
    base_url = "https://www.naukri.com/jobapi/v3/search"
    delay = settings.NAUKRI_DELAY
    band_delay = settings.NAUKRI_BAND_DELAY
    jobs_per_page = settings.NAUKRI_JOBS_PER_PAGE
    max_pages = settings.NAUKRI_MAX_PAGES

    def __init__(self, proxies=None, ca_cert=None):
        super().__init__(Site.NAUKRI, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=self.ca_cert,
            is_tls=False,
            has_retry=True,
            delay=self.delay,
            clear_cookies=True,
        )
        self.headers = {
            "authority": "www.naukri.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "appid": "109",
            "systemid": "Naukri",
            "Nkparam": "Ppy0YK9uSHqPtG3bEejYc04RTpUN2CjJOrqA68tzQt0SKJHXZKzz9M8cZtKLVkoOuQmfe4cTb1r2CwfHaxW5Tg==",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.session.headers.update(self.headers)
        self.scraper_input = None
        self.country = "India"

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        page = (scraper_input.offset // self.jobs_per_page) + 1 if scraper_input.offset else 1
        request_count = 0
        seconds_old = scraper_input.hours_old * 3600 if scraper_input.hours_old else None
        continue_search = lambda: len(job_list) < scraper_input.results_wanted and page <= self.max_pages
        while continue_search():
            request_count += 1
            log.info(f"Naukri page {request_count} / {math.ceil(scraper_input.results_wanted / self.jobs_per_page)}")
            params = {
                "noOfResults": self.jobs_per_page,
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": scraper_input.search_term,
                "pageNo": page,
                "k": scraper_input.search_term,
                "seoKey": f"{scraper_input.search_term.lower().replace(' ', '-')}-jobs",
                "src": "jobsearchDesk",
                "latLong": "",
                "location": scraper_input.location,
                "remote": "true" if scraper_input.is_remote else None,
            }
            if seconds_old:
                params["days"] = seconds_old // 86400
            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = self.session.get(self.base_url, params=params, timeout=10)
                if response.status_code not in range(200, 400):
                    err = f"Naukri API response status code {response.status_code}"
                    log.error(err)
                    return JobResponse(jobs=job_list)
                data = response.json()
                job_details = data.get("jobDetails", [])
                if not job_details:
                    break
            except Exception as e:
                log.error(f"Naukri API request failed: {str(e)}")
                return JobResponse(jobs=job_list)

            for job in job_details:
                job_id = job.get("jobId")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                try:
                    job_post = self._process_job(job, job_id, scraper_input.linkedin_fetch_description)
                    if job_post: job_list.append(job_post)
                    if not continue_search(): break
                except Exception as e:
                    log.exception("Naukri job processing error")
                    raise NaukriException(str(e))
            if continue_search():
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                page += 1
        job_list = job_list[:scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_job(self, job: dict, job_id: str, full_descr: bool) -> Optional[JobPost]:
        title = job.get("title", "N/A")
        company = job.get("companyName", "N/A")
        company_url = f"https://www.naukri.com{job.get('staticUrl', '')}" if job.get("staticUrl") else None
        location = self._get_location(job.get("placeholders", []))
        compensation = self._get_compensation(job.get("placeholders", []))
        date_posted = self._parse_date(job.get("footerPlaceholderLabel"), job.get("createdDate"))
        job_url = f"https://www.naukri.com{job.get('jdURL', f'/job/{job_id}')}"
        description = job.get("jobDescription") if full_descr else None
        if description and self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
            description = markdown_converter(description)
        job_type = parse_job_type(description) if description else None
        company_industry = parse_company_industry(description) if description else None
        is_remote = is_job_remote(title, description or "", location)
        company_logo = job.get("logoPathV3") or job.get("logoPath")
        skills = job.get("tagsAndSkills", "").split(",") if job.get("tagsAndSkills") else None
        experience_range = job.get("experienceText")
        ambition = job.get("ambitionBoxData", {})
        company_rating = float(ambition.get("AggregateRating")) if ambition.get("AggregateRating") else None
        company_reviews_count = ambition.get("ReviewsCount")
        vacancy_count = job.get("vacancy")
        work_from_home_type = self._infer_work_from_home_type(job.get("placeholders", []), title, description or "")

        return JobPost(
            id=f"nk-{job_id}",
            title=title,
            company_name=company,
            company_url=company_url,
            location=location,
            is_remote=is_remote,
            date_posted=date_posted,
            job_url=job_url,
            compensation=compensation,
            job_type=job_type,
            company_industry=company_industry,
            description=description,
            emails=extract_emails_from_text(description or ""),
            company_logo=company_logo,
            skills=skills,
            experience_range=experience_range,
            company_rating=company_rating,
            company_reviews_count=company_reviews_count,
            vacancy_count=vacancy_count,
            work_from_home_type=work_from_home_type,
        )

    def _get_location(self, placeholders: list[dict]) -> Location:
        location = Location(country=Country.from_string(self.country))
        for p in placeholders:
            if p.get("type") == "location":
                loc_str = p.get("label", "")
                parts = loc_str.split(", ")
                city = parts[0] if parts else None
                state = parts[1] if len(parts) > 1 else None
                location = Location(city=city, state=state, country=Country.from_string(self.country))
                break
        return location

    def _get_compensation(self, placeholders: list[dict]) -> Optional[Compensation]:
        for p in placeholders:
            if p.get("type") == "salary":
                salary_text = p.get("label", "").strip()
                if salary_text == "Not disclosed": return None
                m = re.match(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(Lacs|Lakh|Cr)\s*(P\.A\.)?", salary_text, re.IGNORECASE)
                if m:
                    min_sal, max_sal, unit = float(m.group(1)), float(m.group(2)), m.group(3)
                    currency = "INR"
                    if unit.lower() in ("lacs", "lakh"):
                        min_sal *= 100000; max_sal *= 100000
                    elif unit.lower() == "cr":
                        min_sal *= 10000000; max_sal *= 10000000
                    return Compensation(min_amount=int(min_sal), max_amount=int(max_sal), currency=currency)
        return None

    def _parse_date(self, label: str, created_date: int) -> Optional[date]:
        today = datetime.now()
        if not label:
            if created_date:
                return datetime.fromtimestamp(created_date / 1000).date()
            return None
        label = label.lower()
        if "today" in label or "just now" in label or "few hours" in label:
            return today.date()
        elif "ago" in label:
            m = re.search(r"(\d+)\s*day", label)
            if m: return (today - timedelta(days=int(m.group(1)))).date()
        elif created_date:
            return datetime.fromtimestamp(created_date / 1000).date()
        return None

    def _infer_work_from_home_type(self, placeholders: list[dict], title: str, description: str) -> Optional[str]:
        loc_str = next((p["label"] for p in placeholders if p["type"] == "location"), "").lower()
        if "hybrid" in loc_str or "hybrid" in title.lower() or "hybrid" in description.lower():
            return "Hybrid"
        elif "remote" in loc_str or "remote" in title.lower() or "remote" in description.lower():
            return "Remote"
        elif "work from office" in description.lower() or not ("remote" in description.lower() or "hybrid" in description.lower()):
            return "Work from office"
        return None

# jobspy/naukri/exception.py
from jobspy.exception import NaukriException

# jobspy/naukri/util.py
from bs4 import BeautifulSoup
from jobspy.model import JobType, Location
from jobspy.util import get_enum_from_job_type

def parse_job_type(soup_or_html) -> list[JobType] | None:
    # Normalize input to BeautifulSoup by stringifying then parsing. This avoids
    # cases where 'soup_or_html' is an object (e.g., markdown string) with a
    # .find method of an unexpected type.
    if not soup_or_html:
        return None
    soup = BeautifulSoup(str(soup_or_html), "html.parser")
    job_type_tag = soup.find("span", class_="job-type")
    if job_type_tag:
        val = job_type_tag.get_text(strip=True).lower().replace("-", "")
        return [get_enum_from_job_type(val)] if val else []
    return None


def parse_company_industry(soup_or_html) -> str | None:
    if not soup_or_html:
        return None
    soup = BeautifulSoup(str(soup_or_html), "html.parser")
    industry_tag = soup.find("span", class_="industry")
    return industry_tag.get_text(strip=True) if industry_tag else None

def is_job_remote(title, description, location) -> bool:
    remote_keywords = ["remote", "work from home", "wfh"]
    loc_str = location.display_location()
    full = f"{title} {description} {loc_str}".lower()
    return any(k in full for k in remote_keywords)