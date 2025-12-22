# jobspy/mock_scrapers.py
from __future__ import annotations
from typing import List
from jobspy.model import Scraper, Site, JobPost, JobResponse, Location


class MockLinkedIn(Scraper):
    def __init__(self, proxies=None, ca_cert=None):
        super().__init__(Site.LINKEDIN, proxies=proxies, ca_cert=ca_cert)

    def scrape(self, scraper_input) -> JobResponse:
        j = JobPost(
            id="li-sample-1",
            title="Sample LinkedIn Job",
            company_name="Acme Co",
            job_url="https://linkedin.example/job/1",
            location=Location(city="Bengaluru", state="Karnataka", country="india"),
            description="Sample job description",
            is_remote=False,
        )
        return JobResponse(jobs=[j])


class MockNaukri(Scraper):
    def __init__(self, proxies=None, ca_cert=None):
        super().__init__(Site.NAUKRI, proxies=proxies, ca_cert=ca_cert)

    def scrape(self, scraper_input) -> JobResponse:
        j = JobPost(
            id="nk-sample-1",
            title="Sample Naukri Job",
            company_name="Beta Ltd",
            job_url="https://naukri.example/job/1",
            location=Location(city="Mumbai", state="Maharashtra", country="india"),
            description="Sample Naukri description",
            is_remote=False,
        )
        return JobResponse(jobs=[j])