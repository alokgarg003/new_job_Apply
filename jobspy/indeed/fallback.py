# jobspy/indeed/fallback.py
"""
Fallback logic: India → Remote (US) when India returns 0 jobs.
"""

import time
import random
from typing import List, Dict, Any
from urllib.parse import urlencode
from jobspy.util import create_logger

log = create_logger("IndeedFallback")

def build_search_url(base_url: str, q: str, l: str, fromage: int, start: int = 0, remote: bool = False) -> str:
    """Build Indeed search URL with query parameters."""
    params = {
        "q": q,
        "l": l,
        "fromage": str(fromage),
        "start": str(start),
    }
    if remote:
        params["remote"] = "on"
    return f"{base_url}/jobs?{urlencode(params)}"

def fetch_page(session, url: str, headers: Dict[str, str]) -> str:
    """Fetch a single page with random jitter and retry."""
    # Random delay 1–3 seconds to avoid burst detection
    time.sleep(random.uniform(1.0, 3.0))
    resp = session.get(url, headers=headers, timeout=15)
    if resp.status_code == 403:
        raise Exception(f"403 Forbidden: {url}")
    resp.raise_for_status()
    return resp.text

def scrape_page_batch(
    session,
    base_url: str,
    q: str,
    l: str,
    fromage: int,
    start: int,
    results_wanted: int,
    headers: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Scrape one page and return jobs."""
    url = build_search_url(base_url, q, l, fromage, start=start)
    html = fetch_page(session, url, headers)
    from .html_parser import extract_all_jobs
    jobs = extract_all_jobs(html)
    return jobs

def scrape_indeed_with_fallback(
    q: str,
    location: str,
    fromage: int,
    results_wanted: int,
    headers: Dict[str, str],
    session,
    india_base="https://in.indeed.com",
    remote_base="https://www.indeed.com",
) -> List[Dict[str, Any]]:
    """
    1) Try India.
    2) If 0 jobs, retry with remote‑friendly US search.
    3) Merge and deduplicate.
    """
    all_jobs = []
    seen = set()

    # India attempt
    log.info(f"Trying India search: q={q}, l={location}, fromage={fromage}")
    start = 0
    while len(all_jobs) < results_wanted:
        batch = scrape_page_batch(session, india_base, q, location, fromage, start, results_wanted, headers)
        if not batch:
            break
        for j in batch:
            key = j.get("jk")
            if key and key not in seen:
                seen.add(key)
                all_jobs.append(j)
        start += len(batch)
        if start >= 1000:  # safety
            break

    if all_jobs:
        log.info(f"India search returned {len(all_jobs)} jobs")
        return all_jobs[:results_wanted]

    # Fallback: Remote
    log.warning("India search returned 0 jobs; falling back to remote search")
    start = 0
    while len(all_jobs) < results_wanted:
        batch = scrape_page_batch(session, remote_base, q + " remote", "", fromage, start, results_wanted, headers)
        if not batch:
            break
        for j in batch:
            key = j.get("jk")
            if key and key not in seen:
                seen.add(key)
                all_jobs.append(j)
        start += len(batch)
        if start >= 1000:
            break

    log.info(f"Remote fallback returned {len(all_jobs)} jobs")
    return all_jobs[:results_wanted]