# jobspy/scrape_jobs.py
from __future__ import annotations
import math
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Union, List
import pandas as pd
from jobspy.model import (
    JobPost, JobResponse, Site, ScraperInput, Country, JobType, CompensationInterval, Location, SalarySource,
)
from jobspy.linkedin import LinkedIn
from jobspy.naukri import Naukri
from jobspy.util import create_logger, extract_salary, create_session, get_enum_from_job_type, map_str_to_site, convert_to_annual, desired_order
import settings

log = create_logger("ScrapeJobs")

SCRAPER_MAPPING = {
    Site.LINKEDIN: LinkedIn,
    Site.NAUKRI: Naukri,
}

# Mapping for dry-run/mock mode (no network)
try:
    from .mock_scrapers import MockLinkedIn, MockNaukri
    MOCK_SCRAPER_MAPPING = {
        Site.LINKEDIN: MockLinkedIn,
        Site.NAUKRI: MockNaukri,
    }
except Exception:
    MOCK_SCRAPER_MAPPING = {}

def set_logger_level(verbose: int):
    level_name = {2: "INFO", 1: "WARNING", 0: "ERROR"}.get(verbose, "INFO")
    level = getattr(logging, level_name.upper(), None)
    if level is not None:
        for logger_name in logging.root.manager.loggerDict:
            if logger_name.startswith("JobSpy:"):
                logging.getLogger(logger_name).setLevel(level)

def scrape_jobs(
    site_name: str | list[str] | Site | list[Site] | None = None,
    search_term: str | None = None,
    google_search_term: str | None = None,
    location: str | None = None,
    distance: int | None = 50,
    is_remote: bool = False,
    job_type: str | None = None,
    easy_apply: bool | None = None,
    results_wanted: int = settings.RESULTS_WANTED,
    country_indeed: str = "usa",
    proxies: list[str] | str | None = settings.PROXIES,
    ca_cert: str | None = settings.CA_CERT,
    description_format: str = settings.DESCRIPTION_FORMAT,
    linkedin_fetch_description: bool | None = settings.LI_FETCH_DESCRIPTION,
    linkedin_company_ids: list[int] | None = None,
    offset: int | None = 0,
    hours_old: int = None,
    enforce_annual_salary: bool = settings.ENFORCE_ANNUAL_SALARY,
    verbose: int = settings.VERBOSE,
    **kwargs,
) -> pd.DataFrame:
    set_logger_level(verbose)
    job_type = get_enum_from_job_type(job_type) if job_type else None
    def get_site_type():
        site_types = list(Site)
        if isinstance(site_name, str): site_types = [map_str_to_site(site_name)]
        elif isinstance(site_name, Site): site_types = [site_name]
        elif isinstance(site_name, list):
            site_types = [map_str_to_site(site) if isinstance(site, str) else site for site in site_name]
        return site_types

    country_enum = Country.from_string(country_indeed)

    scraper_input = ScraperInput(
        site_type=get_site_type(),
        country=country_enum,
        search_term=search_term,
        google_search_term=google_search_term,
        location=location,
        distance=distance,
        is_remote=is_remote,
        job_type=job_type,
        easy_apply=easy_apply,
        description_format=description_format,
        linkedin_fetch_description=linkedin_fetch_description,
        results_wanted=results_wanted,
        linkedin_company_ids=linkedin_company_ids,
        offset=offset,
        hours_old=hours_old,
    )

    def scrape_site(site: Site) -> tuple[str, JobResponse]:
        # Use mock scrapers in DRY_RUN mode to avoid network calls
        if getattr(settings, "DRY_RUN", False) and site in MOCK_SCRAPER_MAPPING:
            scraper_class = MOCK_SCRAPER_MAPPING[site]
        else:
            scraper_class = SCRAPER_MAPPING[site]
        scraper = scraper_class(proxies=proxies, ca_cert=ca_cert)
        scraped_data: JobResponse = scraper.scrape(scraper_input)
        cap_name = site.value.capitalize()
        site_name = "ZipRecruiter" if cap_name == "Zip_recruiter" else cap_name
        create_logger(site_name).info(f"finished scraping")
        return site.value, scraped_data

    site_to_jobs_dict = {}

    def worker(site):
        site_val, scraped_info = scrape_site(site)
        return site_val, scraped_info

    with ThreadPoolExecutor() as executor:
        future_to_site = {executor.submit(worker, site): site for site in scraper_input.site_type}
        for future in as_completed(future_to_site):
            site_value, scraped_data = future.result()
            site_to_jobs_dict[site_value] = scraped_data

    jobs_dfs: list[pd.DataFrame] = []
    for site, job_response in site_to_jobs_dict.items():
        for job in job_response.jobs:
            job_data = job.dict()
            job_url = job_data["job_url"]
            job_data["site"] = site
            job_data["company"] = job_data["company_name"]
            job_data["job_type"] = (
                ", ".join(job_type.value[0] for job_type in job_data["job_type"])
                if job_data["job_type"]
                else None
            )
            job_data["emails"] = (
                ", ".join(job_data["emails"]) if job_data["emails"] else None
            )
            if job_data["location"]:
                job_data["location"] = Location(**job_data["location"]).display_location()

            compensation_obj = job_data.get("compensation")
            if compensation_obj and isinstance(compensation_obj, dict):
                job_data["interval"] = (
                    compensation_obj.get("interval").value
                    if compensation_obj.get("interval")
                    else None
                )
                job_data["min_amount"] = compensation_obj.get("min_amount")
                job_data["max_amount"] = compensation_obj.get("max_amount")
                job_data["currency"] = compensation_obj.get("currency", "USD")
                job_data["salary_source"] = SalarySource.DIRECT_DATA.value
                if enforce_annual_salary and (
                    job_data["interval"]
                    and job_data["interval"] != "yearly"
                    and job_data["min_amount"]
                    and job_data["max_amount"]
                ):
                    convert_to_annual(job_data)
            else:
                if country_enum == Country.USA:
                    (
                        job_data["interval"],
                        job_data["min_amount"],
                        job_data["max_amount"],
                        job_data["currency"],
                    ) = extract_salary(
                        job_data["description"],
                        enforce_annual=enforce_annual_salary,
                    )
                    job_data["salary_source"] = SalarySource.DESCRIPTION.value

            job_data["salary_source"] = (
                job_data["salary_source"]
                if "min_amount" in job_data and job_data["min_amount"]
                else None
            )

            job_data["skills"] = (
                ", ".join(job_data["skills"]) if job_data["skills"] else None
            )
            job_data["experience_range"] = job_data.get("experience_range")
            job_data["company_rating"] = job_data.get("company_rating")
            job_data["company_reviews_count"] = job_data.get("company_reviews_count")
            job_data["vacancy_count"] = job_data.get("vacancy_count")
            job_data["work_from_home_type"] = job_data.get("work_from_home_type")

            job_df = pd.DataFrame([job_data])
            jobs_dfs.append(job_df)

    if jobs_dfs:
        filtered_dfs = [df.dropna(axis=1, how="all") for df in jobs_dfs]
        jobs_df = pd.concat(filtered_dfs, ignore_index=True)
        for column in desired_order:
            if column not in jobs_df.columns:
                jobs_df[column] = None
        jobs_df = jobs_df[desired_order]
        return jobs_df.sort_values(
            by=["site", "date_posted"], ascending=[True, False]
        ).reset_index(drop=True)
    else:
        return pd.DataFrame()

def convert_to_annual(job_data: dict):
    if job_data["interval"] == "hourly":
        job_data["min_amount"] *= 2080
        job_data["max_amount"] *= 2080
    if job_data["interval"] == "monthly":
        job_data["min_amount"] *= 12
        job_data["max_amount"] *= 12
    if job_data["interval"] == "weekly":
        job_data["min_amount"] *= 52
        job_data["max_amount"] *= 52
    if job_data["interval"] == "daily":
        job_data["min_amount"] *= 260
        job_data["max_amount"] *= 260
    job_data["interval"] = "yearly"