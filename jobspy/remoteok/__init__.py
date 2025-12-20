from __future__ import annotations

from jobspy.model import Scraper, ScraperInput, JobResponse, Site
from jobspy.util import create_logger

log = create_logger("RemoteOK")


class RemoteOK(Scraper):
    """Placeholder RemoteOK scraper. Returns empty results until implemented."""

    def __init__(self, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        super().__init__(Site.REMOTEOK, proxies=proxies, ca_cert=ca_cert)

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        log.info("RemoteOK: placeholder scraper called — returning empty JobResponse")
        return JobResponse(jobs=[])
