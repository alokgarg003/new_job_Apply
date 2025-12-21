# jobspy/google/google.py
"""
Google Jobs scraper for public discovery.
Supports India queries with global fallback and cursor pagination.
"""
from __future__ import annotations
import math
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import urlencode

from jobspy.util import create_logger, create_session, extract_emails_from_text, extract_job_type
from jobspy.model import ScraperInput, Site, JobPost, JobResponse, Location
from jobspy.google.constant import headers_initial, headers_jobs

log = create_logger("Google")

class Google:
    def __init__(self, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        self.site = Site.GOOGLE
        self.session = create_session(
            is_tls=True,
            proxies=proxies,
            ca_cert=ca_cert,
            has_retry=True,
            delay=3,
            clear_cookies=True
        )

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrape jobs via Google Jobs with fallbacks.
        """

        jobs_per_page = 10
        base_url = "https://www.google.com/search"
        results_wanted = min(100, scraper_input.results_wanted)
        loc = scraper_input.location or ""

        # Google's internal cursor API domain
        jobs_api_host = "https://www.google.com/async/callback:550"

        # Fallback query creation logic
        def build_query(keyword: str, remote=False) -> str:
            q = f"{keyword} job"
            if remote:
                q += " remote"
            if loc:
                q += f" near {loc}"
            return q

        # Step 1: Try India-localized search
        job_results = []
        seen_urls = set()

        retry_with_global = False

        searches_to_try = [
            {"q": build_query(scraper_input.search_term), "loc": scraper_input.location},
            {"q": build_query(scraper_input.search_term, remote=True), "loc": "Remote"}
        ]

        if loc.lower() == "india":
            retry_with_global = True

        for search in searches_to_try:
            try:
                url_params = {
                    "q": search["q"],
                    "udm": "8"
                }
                url = f"{base_url}?{urlencode(url_params)}"
                self.session.headers.update(headers_initial)

                response = self.session.get(url, timeout=15)
                html_content = response.text

                # Extract first batch of jobs from initial page
                initial_jobs = self._extract_jobs_from_html(html_content)
                job_results.extend(initial_jobs)
                log.info(f"Discovered {len(initial_jobs)} Google jobs via '{search['q']}' ({search.get('loc', '')})")

                # Check for more pages via async cursor
                fc_match = re.search(r'data-async-fc="([^"]+)"', html_content)
                forward_cursor = fc_match.groups(0)[0] if fc_match else None

                page = 1
                while forward_cursor and len(job_results) < results_wanted:
                    next_jobs, forward_cursor = self._fetch_next_page(jobs_api_host, forward_cursor)
                    job_results.extend(next_jobs)
                    page += 1
                    log.debug(f"Fetched Google jobs page {page} ({len(next_jobs)} results)")

                    if len(job_results) >= results_wanted:
                        break

                if job_results:
                    break
            except Exception as e:
                log.warning(f"Google query error with '{search['q']}': {str(e)}")

        # Prune duplicates and filter fresh jobs
        unique_jobs = []
        for j in job_results:
            if j.job_url not in seen_urls:
                seen_urls.add(j.job_url)
                unique_jobs.append(j)

        return JobResponse(jobs=unique_jobs[:results_wanted])

    def _fetch_next_page(self, jobs_api_host: str, forward_cursor: str) -> tuple[List[JobPost], str | None]:
        """
        Fetch next page of Google jobs using the async cursor API.
        """
        params = {
            "fc": [forward_cursor],
            "fcv": "3"
        }
        self.session.headers.update(headers_jobs)
        res = self.session.get(jobs_api_host, params=params, timeout=15)

        if res.status_code != 200:
            log.error(f"Non-200 response from Google Jobs cursor URL: {res.status_code}")
            return [], None

        raw_data = res.text
        json_matches = re.findall(r'\[\[\[.*?(?=\]\]\])\]\]\]', raw_data, re.DOTALL)

        results = []
        next_cursor = None

        for i, match in enumerate(json_matches):
            try:
                parsed = json.loads(match)

                for item in parsed:
                    job_type, content = item
                    if not content.startswith('[['):
                        continue

                    job_data = json.loads(content)
                    jobs_list = job_data.get("520084652")
                    if not jobs_list:
                        continue

                    for job_card in jobs_list:
                        job = self._parse_job_card(job_card)
                        if job:
                            results.append(job)

                    if i < len(json_matches) - 1:
                        cursor_match = re.search(r'data-async-fc="([^"]+)"', match)
                        next_cursor = cursor_match.groups(0)[0] if cursor_match else None
            except Exception as e:
                log.error(f"Error parsing Google jobs result: {e}")

        return results, next_cursor

    def _extract_jobs_from_html(self, html: str) -> List[JobPost]:
        jobs = []
        pattern = re.compile(r'\[\[\[[^\]]*?("520084652"[^\]]*\]\]\])', re.DOTALL)
        matches = pattern.findall(html)

        for match in matches:
            try:
                data = json.loads(match)
                for item in data:
                    if isinstance(item, list) and item:
                        key, payload = item
                        if key == '520084652':
                            cards = payload if isinstance(payload, list) else []
                            for card in cards:
                                job = self._parse_job_card(card)
                                if job:
                                    jobs.append(job)
                            break
            except Exception as e:
                log.warn(f"Bad JSON in extraction: {e}")
        return jobs

    def _parse_job_card(self, job_card: dict) -> JobPost | None:
        """
        Extract structured job data from a jobCard object.
        """
        try:
            # Unpack data safely
            title = job_card[0] if len(job_card) > 0 else ""
            company = job_card[1] if len(job_card) > 1 else ""
            location_string = job_card[2] if len(job_card) > 2 else ""
            date_posted_str = job_card[12] if len(job_card) > 12 else ""
            job_url = job_card[3][0][0] if len(job_card) > 3 and job_card[3] and isinstance(job_card[3], list) and len(job_card[3]) >0 else ""
            description = job_card[19] if len(job_card) > 19 else ""

            # Parse date
            date_posted = None
            if isinstance(date_posted_str, str) and 'day' in date_posted_str.lower():
                try:
                    days_ago = int(re.search(r"(\d+)", date_posted_str).group())
                    date_posted = datetime.now().date() - timedelta(days=days_ago)
                except Exception:
                    pass

            # Parse location
            city, state, country = None, None, None
            if ',' in location_string:
                parts = [p.strip() for p in location_string.split(",")]
                city = parts[0] if len(parts) >= 1 else None
                state = parts[1] if len(parts) >= 2 else None
                country = parts[-1] if len(parts) >= 3 else None

            # Avoid duplicate undetected fields without erroring
            job = JobPost(
                id=f"go-{company}-{title}-{date_posted.strftime('%Y-%m-%d') if date_posted else 'no-date'}",
                title=title,
                company_name=company,
                location=Location(city=city, state=state, country=country),
                date_posted=date_posted,
                job_url=job_url,
                jobs_source="google",
                description=description,
                job_type=extract_job_type(description),
                is_remote="remote" in description.lower() or "wfh" in description.lower(),
                emails=extract_emails_from_text(description)
            )

            return job
        except Exception as e:
            log.warn(f"Failed to parse Google job: {e}")
            return None