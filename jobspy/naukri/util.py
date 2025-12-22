# jobspy/naukri/util.py
from bs4 import BeautifulSoup
from jobspy.model import JobType, Location
from jobspy.util import get_enum_from_job_type

def parse_job_type(soup_or_html) -> list[JobType] | None:
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