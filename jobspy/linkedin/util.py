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