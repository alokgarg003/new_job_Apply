from __future__ import annotations

from jobspy.model import Scraper, ScraperInput, JobResponse, Site
from jobspy.util import create_logger

log = create_logger("Dice")


class Dice(Scraper):
    """Placeholder Dice scraper. Returns empty results until fully implemented."""

    def __init__(self, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        super().__init__(Site.DICE, proxies=proxies, ca_cert=ca_cert)

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        log.info("Dice: placeholder scraper called — returning empty JobResponse")
        return JobResponse(jobs=[])
