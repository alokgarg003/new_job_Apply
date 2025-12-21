# jobspy/glassdoor/glassdoor.py
"""Full Glassdoor scraper – implements the Scraper interface used by jobspy."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Local imports from jobspy
from jobspy.glassdoor.constant import fallback_token, query_template, headers
from jobspy.glassdoor.util import (
    get_cursor_for_page,
    parse_compensation,
    parse_location,
)
from jobspy.util import (
    extract_emails_from_text,
    create_logger,
    create_session,
    markdown_converter,
)
from jobspy.exception import GlassdoorException
from jobspy.model import (
    JobPost,
    JobResponse,
    DescriptionFormat,
    Scraper,
    ScraperInput,
    Site,
    Compensation,
    CompensationInterval,
    Location,
    JobType,
)

log = create_logger("Glassdoor")


class Glassdoor(Scraper):
    """
    Scraper that uses Glassdoor's GraphQL endpoints.

    The class follows the same public API:
    >>> g = Glassdoor()
    >>> response = g.scrape(scraper_input)
    """

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
    ) -> None:
        site = Site(Site.GLASSDOOR)
        super().__init__(site, proxies=proxies, ca_cert=ca_cert)

        self.base_url: Optional[str] = None
        self.session: Optional[requests.Session] = None
        self.scraper_input: Optional[ScraperInput] = None

        self.jobs_per_page: int = 30
        self.max_pages: int = 30
        self.seen_urls: set[str] = set()

    # ------------------------------------------------------------------ #
    # Core entry point
    # ------------------------------------------------------------------ #

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Run a full search.

        ``scraper_input`` already holds all user‑supplied filters; this
        method orchestrates pagination, data extraction and object conversion.
        """
        self.scraper_input = scraper_input
        self.scraper_input.results_wanted = min(900, scraper_input.results_wanted)

        # Figure out the proper base URL based on country enum.
        self.base_url = self.scraper_input.country.get_glassdoor_url()

        # Keep a single session – it handles proxies, redirection, retries,
        # and the CSRF token that the API requires.
        self.session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, has_retry=True
        )

        # CSRF token
        token = self._get_csrf_token()
        headers["gd-csrf-token"] = token if token else fallback_token
        self.session.headers.update(headers)

        loc_id, loc_type = self._get_location(
            scraper_input.location, scraper_input.is_remote
        )
        if loc_type is None:
            log.error("Glassdoor: location not parsed")
            return JobResponse(jobs=[])

        job_list: List[JobPost] = []
        cursor: Optional[str] = None

        # Determine how many pages to request.
        start_page = 1 + (scraper_input.offset // self.jobs_per_page)
        total_pages_needed = (
            scraper_input.results_wanted // self.jobs_per_page
        ) + 2
        end_page = min(total_pages_needed, self.max_pages + 1)

        for page in range(start_page, end_page):
            log.info(f"search page: {page} / {end_page - 1}")
            try:
                jobs, cursor = self._fetch_jobs_page(
                    scraper_input, loc_id, loc_type, page, cursor
                )
                job_list.extend(jobs)
                if not jobs or len(job_list) >= scraper_input.results_wanted:
                    job_list = job_list[: scraper_input.results_wanted]
                    break
            except Exception as exc:  # pragma: no cover
                log.error(f"Glassdoor: {exc}")
                break

        return JobResponse(jobs=job_list)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _fetch_jobs_page(
        self,
        scraper_input: ScraperInput,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: Optional[str],
    ) -> Tuple[List[JobPost], Optional[str]]:
        """
        Pull a single page from the GraphQL endpoint and convert each
        entry into a :class:`JobPost`.  The function uses a thread‑pool to
        parallelise the heavy text extraction part.
        """
        payload = self._build_payload(
            location_id=location_id,
            location_type=location_type,
            page_num=page_num,
            cursor=cursor,
        )

        try:
            response = self.session.post(
                f"{self.base_url}/graph",
                data=payload,
                timeout=15,
            )
            if response.status_code != 200:
                raise GlassdoorException(
                    f"bad response status code: {response.status_code}"
                )
            api_res = response.json()[0]
            if "errors" in api_res:
                raise ValueError("Error encountered in API response")
        except Exception as exc:  # pragma: no cover
            log.error(f"Glassdoor: {exc}")
            return [], None

        job_results = api_res["data"]["jobListings"]["jobListings"]

        # Process each job concurrently.  The description fetch is
        # the longest part, so a ThreadPool keeps the main thread free.
        jobs: List[JobPost] = []
        with ThreadPoolExecutor(max_workers=self.jobs_per_page) as executor:
            future_to_job = {
                executor.submit(self._process_job, job): job for job in job_results
            }
            for future in as_completed(future_to_job):
                try:
                    job_post = future.result()
                    if job_post:
                        jobs.append(job_post)
                except Exception as exc:  # pragma: no cover
                    log.exception(f"Glassdoor: error processing a job: {exc}")

        next_cursor = get_cursor_for_page(
            api_res["data"]["jobListings"]["paginationCursors"],
            page_num + 1,
        )
        return jobs, next_cursor

    # ------------------------------------------------------------------ #
    # Build request payload
    # ------------------------------------------------------------------ #

    def _build_payload(
        self,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: Optional[str] = None,
    ) -> str:
        """
        Construct the JSON payload used for every request.
        """
        from_age: Optional[int] = None
        if self.scraper_input.hours_old:
            from_age = max(self.scraper_input.hours_old // 24, 1)

        filter_params: List[dict] = []
        if self.scraper_input.easy_apply:
            filter_params.append({"filterKey": "applicationType", "values": "1"})
        if from_age:
            filter_params.append({"filterKey": "fromAge", "values": str(from_age)})

        payload = {
            "operationName": "JobSearchResultsQuery",
            "variables": {
                "excludeJobListingIds": [],
                "filterParams": filter_params,
                "keyword": self.scraper_input.search_term,
                "numJobsToShow": self.jobs_per_page,
                "locationType": location_type,
                "locationId": int(location_id),
                "parameterUrlInput": f"IL.0,12_I{location_type}{location_id}",
                "pageNumber": page_num,
                "pageCursor": cursor,
                "fromage": from_age,
                "sort": "date",
            },
            "query": query_template,
        }

        # Optional job‑type filter
        if self.scraper_input.job_type:
            payload["variables"]["filterParams"].append(
                {"filterKey": "jobType", "values": self.scraper_input.job_type.value[0]}
            )

        return json.dumps([payload])

    # ------------------------------------------------------------------ #
    # Parse a single job entry into a JobPost model
    # ------------------------------------------------------------------ #

    def _process_job(self, raw_job: dict) -> Optional[JobPost]:
        """
        Convert the raw ``jobview`` dict into a fully‑filled JobPost.
        """
        jobview = raw_job["jobview"]
        job_id = jobview["job"]["listingId"]
        job_url = f"{self.base_url}job-listing/j?jl={job_id}"

        if job_url in self.seen_urls:
            return None
        self.seen_urls.add(job_url)

        title = jobview["job"]["jobTitleText"]
        company_name = jobview["header"]["employerNameFromSearch"]
        company_id = jobview["header"]["employer"]["id"]
        location_name = jobview["header"].get("locationName", "")
        location_type = jobview["header"].get("locationType", "")
        age_in_days = jobview["header"].get("ageInDays")

        # Determine remote / physical setting
        is_remote = location_type == "S"
        location: Optional[Location] = None
        if not is_remote:
            location = parse_location(location_name)

        date_posted: Optional[datetime] = (
            datetime.now() - timedelta(days=age_in_days) if age_in_days else None
        )

        compensation = parse_compensation(jobview["header"])

        try:
            description = self._fetch_job_description(job_id)
        except Exception:  # pragma: no cover
            description = None

        company_url = (
            f"{self.base_url}Overview/W-EI_IE{company_id}.htm" if company_id else None
        )
        company_logo = jobview.get("overview", {}).get("squareLogoUrl")

        listing_type = jobview.get("header", {}).get("adOrderSponsorshipLevel", "").lower()

        return JobPost(
            id=f"gd-{job_id}",
            title=title,
            company_url=company_url,
            company_name=company_name,
            date_posted=date_posted,
            job_url=job_url,
            location=location,
            compensation=compensation,
            is_remote=is_remote,
            description=description,
            emails=extract_emails_from_text(description) if description else None,
            company_logo=company_logo,
            listing_type=listing_type,
        )

    # ------------------------------------------------------------------ #
    # Description fetch
    # ------------------------------------------------------------------ #

    def _fetch_job_description(self, job_id: str) -> Optional[str]:
        """
        Call the JobDetailQuery GraphQL operation to pull the full description.
        """
        body = [
            {
                "operationName": "JobDetailQuery",
                "variables": {
                    "jl": job_id,
                    "queryString": "q",
                    "pageTypeEnum": "SERP",
                },
                "query": """
                query JobDetailQuery($jl: Long!, $queryString: String, $pageTypeEnum: PageTypeEnum) {
                  jobview: jobView(
                    listingId: $jl
                    contextHolder: { queryString: $queryString, pageTypeEnum: $pageTypeEnum }
                  ) {
                    job {
                      description
                      __typename
                    }
                    __typename
                  }
                }
                """,
            }
        ]

        resp = self.session.post(
            f"{self.base_url}/graph",
            json=body,
            headers=headers,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()[0]
        desc = data["data"]["jobview"]["job"]["description"]

        if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
            desc = markdown_converter(desc)

        return desc

    # ------------------------------------------------------------------ #
    # Location resolution
    # ------------------------------------------------------------------ #

    def _get_location(
        self, location: str | None, is_remote: bool
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Resolve a human string into Glassdoor’s numeric ID and type.

        Remote jobs are represented internally with the ID *11047* and
        type ``STATE`` – this is a magic value understood by the API.
        """
        if not location or is_remote:
            return 11047, "STATE"

        url = f"{self.base_url}/findPopularLocationAjax.htm?maxLocationsToReturn=10&term={location}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            if resp.status_code == 429:
                log.error("429 Response - Blocked by Glassdoor for too many requests")
            else:
                log.error(f"Glassdoor response status-code {resp.status_code}: {resp.text}")
            return None, None

        items = resp.json()
        if not items:
            raise ValueError(f"Location '{location}' not found on Glassdoor")

        location_type = items[0]["locationType"]
        if location_type == "C":
            location_type = "CITY"
        elif location_type == "S":
            location_type = "STATE"
        elif location_type == "N":
            location_type = "COUNTRY"

        return int(items[0]["locationId"]), location_type