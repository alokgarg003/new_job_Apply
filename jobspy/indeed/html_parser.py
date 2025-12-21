# jobspy/indeed/html_parser.py
"""
HTML and JSON extraction helpers for Indeed search pages.
"""

import json
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


def extract_ld_json_scripts(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract structured data from <script type="application/ld+json">."""
    scripts = soup.find_all("script", type="application/ld+json")
    data = []
    for s in scripts:
        try:
            data.append(json.loads(s.string))
        except json.JSONDecodeError:
            continue
    return data


def extract_mosaic_provider_data(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract embedded JSON from window.mosaic.providerData or jobCardsModel."""
    pattern = re.compile(r"window\.mosaic\.providerData\s*=\s*({.*?});", re.S)
    script = soup.find("script", string=pattern)
    if script:
        match = pattern.search(script.string)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


def extract_job_cards_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract job cards from HTML using data-jk and testid selectors."""
    cards = []
    for card in soup.find_all("div", {"data-jk": True}):
        jk = card["data-jk"]
        title_tag = card.find(["h2", "h3"], string=True)
        title = title_tag.get_text(strip=True) if title_tag else ""
        company_tag = card.find("span", class_=re.compile("company"))
        company = company_tag.get_text(strip=True) if company_tag else ""
        location_tag = card.find("div", class_=re.compile("location"))
        location = location_tag.get_text(strip=True) if location_tag else ""
        link_tag = card.find("a", href=True)
        link = link_tag["href"] if link_tag else ""
        if jk and (title or company):
            cards.append({
                "jk": jk,
                "title": title,
                "company": company,
                "location": location,
                "link": link,
            })
    return cards


def extract_jobs_from_ld_json(ld_json: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert ld+json job postings to simple dicts."""
    jobs = []
    for entry in ld_json:
        if entry.get("@type") == "JobPosting":
            jobs.append({
                "jk": entry.get("identifier", {}).get("value", ""),
                "title": entry.get("title", ""),
                "company": entry.get("hiringOrganization", {}).get("name", ""),
                "location": entry.get("jobLocation", {}).get("address", {}).get("addressLocality", ""),
                "link": entry.get("url", ""),
            })
    return jobs


def extract_jobs_from_mosaic(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract jobs from Indeed's mosaic data structure."""
    jobs = []
    results = data.get("results", [])
    for res in results:
        jk = res.get("jk")
        title = res.get("title", "")
        company = res.get("company", {}).get("displayName", "")
        location = res.get("formattedLocation", "")
        link = res.get("detailUrl", "")
        if jk:
            jobs.append({
                "jk": jk,
                "title": title,
                "company": company,
                "location": location,
                "link": link,
            })
    return jobs


def extract_all_jobs(html: str) -> List[Dict[str, Any]]:
    """Extract jobs with multiple fallback strategies."""
    soup = BeautifulSoup(html, "html.parser")
    all_jobs = []

    # 1) Structured data
    ld_json = extract_ld_json_scripts(soup)
    all_jobs.extend(extract_jobs_from_ld_json(ld_json))

    # 2) Mosaic provider data
    mosaic = extract_mosaic_provider_data(soup)
    if mosaic:
        all_jobs.extend(extract_jobs_from_mosaic(mosaic))

    # 3) HTML job cards
    all_jobs.extend(extract_job_cards_from_html(soup))

    # Deduplicate by jk
    seen = set()
    unique = []
    for j in all_jobs:
        key = j.get("jk")
        if key and key not in seen:
            seen.add(key)
            unique.append(j)
    return unique