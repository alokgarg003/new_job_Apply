# jobspy/model.py
"""
Pydantic data contract – all public data structures used by the scrapers.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# 1️⃣  Job type
# --------------------------------------------------------------------------- #
class JobType(Enum):
    FULL_TIME = (
        "fulltime",
        "períodointegral",
        "estágio/trainee",
        "cunormăîntreagă",
        "tiempocompleto",
        "vollzeit",
        "voltijds",
        "tempointegral",
        "全职",
        "plnýúvazek",
        "fuldtid",
        "دوامكامل",
        "kokopäivätyö",
        "tempsplein",
        "vollzeit",
        "πλήρηςαπασχόληση",
        "teljesmunkaidő",
        "tempopieno",
        "tempsplein",
        "heltid",
        "jornadacompleta",
        "pełnyetat",
        "정규직",
        "100%",
        "全職",
        "งานประจำ",
        "tamzamanlı",
        "повназайнятість",
        "toànthờigian",
    )
    PART_TIME = ("parttime", "teilzeit", "částečnýúvazek", "deltid")
    CONTRACT = ("contract", "contractor")
    TEMPORARY = ("temporary",)
    INTERNSHIP = (
        "internship",
        "prácticas",
        "ojt(onthejobtraining)",
        "praktikum",
        "praktik",
    )

    PER_DIEM = ("perdiem",)
    NIGHTS = ("nights",)
    OTHER = ("other",)
    SUMMER = ("summer",)
    VOLUNTEER = ("volunteer",)


# --------------------------------------------------------------------------- #
# 2️⃣  Country mapping (used for Indeed & Glassdoor)
# --------------------------------------------------------------------------- #
class Country(Enum):
    """
    Mapping of a country to the sub‑domains used by the services.
    Each enum has a *value* tuple:
        (human readable, indeed sub-domain, glassdoor sub-domain)
    """
    ARGENTINA = ("argentina", "ar", "com.ar")
    AUSTRALIA = ("australia", "au", "com.au")
    AUSTRIA = ("austria", "at", "at")
    BAHRAIN = ("bahrain", "bh")
    BELGIUM = ("belgium", "be", "fr:be")
    BULGARIA = ("bulgaria", "bg")
    BRAZIL = ("brazil", "br", "com.br")
    CANADA = ("canada", "ca", "ca")
    CHILE = ("chile", "cl")
    CHINA = ("china", "cn")
    COLOMBIA = ("colombia", "co")
    COSTARICA = ("costa rica", "cr")
    CROATIA = ("croatia", "hr")
    CYPRUS = ("cyprus", "cy")
    CZECHREPUBLIC = ("czech republic,czechia", "cz")
    DENMARK = ("denmark", "dk")
    ECUADOR = ("ecuador", "ec")
    EGYPT = ("egypt", "eg")
    ESTONIA = ("estonia", "ee")
    FINLAND = ("finland", "fi")
    FRANCE = ("france", "fr", "fr")
    GERMANY = ("germany", "de", "de")
    GREECE = ("greece", "gr")
    HONGKONG = ("hong kong", "hk", "com.hk")
    HUNGARY = ("hungary", "hu")
    INDIA = ("india", "in", "co.in")
    INDONESIA = ("indonesia", "id")
    IRELAND = ("ireland", "ie", "ie")
    ISRAEL = ("israel", "il")
    ITALY = ("italy", "it", "it")
    JAPAN = ("japan", "jp")
    KUWAIT = ("kuwait", "kw")
    LATVIA = ("latvia", "lv")
    LITHUANIA = ("lithuania", "lt")
    LUXEMBOURG = ("luxembourg", "lu")
    MALAYSIA = ("malaysia", "malaysia:my", "com")
    MALTA = ("malta", "malta:mt", "mt")
    MEXICO = ("mexico", "mx", "com.mx")
    MOROCCO = ("morocco", "ma")
    NETHERLANDS = ("netherlands", "nl", "nl")
    NEWZEALAND = ("new zealand", "nz", "co.nz")
    NIGERIA = ("nigeria", "ng")
    NORWAY = ("norway", "no")
    OMAN = ("oman", "om")
    PAKISTAN = ("pakistan", "pk")
    PANAMA = ("panama", "pa")
    PERU = ("peru", "pe")
    PHILIPPINES = ("philippines", "ph")
    POLAND = ("poland", "pl")
    PORTUGAL = ("portugal", "pt")
    QATAR = ("qatar", "qa")
    ROMANIA = ("romania", "ro")
    SAUDIARABIA = ("saudi arabia", "sa")
    SINGAPORE = ("singapore", "sg", "sg")
    SLOVAKIA = ("slovakia", "sk")
    SLOVENIA = ("slovenia", "sl")
    SOUTHAFRICA = ("south africa", "za")
    SOUTHKOREA = ("south korea", "kr")
    SPAIN = ("spain", "es", "es")
    SWEDEN = ("sweden", "se")
    SWITZERLAND = ("switzerland", "ch", "de:ch")
    TAIWAN = ("taiwan", "tw")
    THAILAND = ("thailand", "th")
    TURKEY = ("türkiye,turkey", "tr")
    UKRAINE = ("ukraine", "ua")
    UNITEDARABEMIRATES = ("united arab emirates", "ae")
    UK = ("uk,united kingdom", "uk:gb", "co.uk")
    USA = ("usa,us,united states", "www:us", "com")
    URUGUAY = ("uruguay", "uy")
    VENEZUELA = ("venezuela", "ve")
    VIETNAM = ("vietnam", "vn", "com")

    # utilities used only inside the library
    US_CANADA = ("usa/ca", "www")
    WORLDWIDE = ("worldwide", "www")

    @property
    def indeed_domain_value(self):
        sub, _, api_code = self.value[1].partition(":")
        return (sub, api_code.upper()) if sub and api_code else (self.value[1], self.value[1].upper())

    @property
    def glassdoor_domain_value(self):
        if len(self.value) == 3:
            sub, _, dom = self.value[2].partition(":")
            return f"{sub}.glassdoor.{dom}" if sub and dom else f"www.glassdoor.{self.value[2]}"
        raise ValueError(f"Glassdoor not available for {self.name}")

    def get_glassdoor_url(self) -> str:
        return f"https://{self.glassdoor_domain_value}/"

    @classmethod
    def from_string(cls, country_str: str):
        """Convert a string to the corresponding Country enum."""
        country_str = country_str.strip().lower()
        for country in cls:
            country_names = country.value[0].split(",")
            if country_str in country_names:
                return country
        raise ValueError(
            f"Invalid country string: '{country_str}'. "
            f"Valid countries are: {', '.join([c.value[0] for c in cls])}"
        )


# --------------------------------------------------------------------------- #
# 3️⃣  Location helper
# --------------------------------------------------------------------------- #
class Location(BaseModel):
    country: Country | str | None = None
    city: Optional[str] = None
    state: Optional[str] = None

    def display_location(self) -> str:
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if isinstance(self.country, str):
            parts.append(self.country)
        elif self.country and self.country not in (Country.US_CANADA, Country.WORLDWIDE):
            name = self.country.value[0]
            name = name.split(",")[0]
            parts.append(name.title() if name not in ("usa", "uk") else name.upper())
        return ", ".join(parts)


# --------------------------------------------------------------------------- #
# 4️⃣  Compensation
# --------------------------------------------------------------------------- #
class CompensationInterval(str, Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"

    @classmethod
    def get_interval(cls, code: str) -> str | None:
        conv = {"YEAR": cls.YEARLY, "HOUR": cls.HOURLY}
        return conv.get(code, cls[code].value if code in cls.__members__ else None)


class Compensation(BaseModel):
    interval: Optional[CompensationInterval] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = "USD"


# --------------------------------------------------------------------------- #
# 5️⃣  Description format
# --------------------------------------------------------------------------- #
class DescriptionFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"


# --------------------------------------------------------------------------- #
# 6️⃣  Base job & response
# --------------------------------------------------------------------------- #
class JobPost(BaseModel):
    id: Optional[str] = None
    title: str
    company_name: Optional[str] = None
    job_url: str
    job_url_direct: Optional[str] = None
    location: Optional[Location] = None

    description: Optional[str] = None
    company_url: Optional[str] = None
    company_url_direct: Optional[str] = None

    job_type: Optional[List[JobType]] = None
    compensation: Optional[Compensation] = None
    date_posted: Optional[date] = None
    emails: Optional[List[str]] = None
    is_remote: Optional[bool] = None
    listing_type: Optional[str] = None

    # LinkedIn
    job_level: Optional[str] = None
    company_industry: Optional[str] = None
    # Indeed
    company_addresses: Optional[str] = None
    company_num_employees: Optional[str] = None
    company_revenue: Optional[str] = None
    company_description: Optional[str] = None
    company_logo: Optional[str] = None
    banner_photo_url: Optional[str] = None
    job_function: Optional[str] = None

    # Naukri specific
    skills: Optional[List[str]] = None
    experience_range: Optional[str] = None
    company_rating: Optional[float] = None
    company_reviews_count: Optional[int] = None
    vacancy_count: Optional[int] = None
    work_from_home_type: Optional[str] = None

    # Enrichment
    site: Optional[str] = None
    key_skills: Optional[List[str]] = None
    match_score: Optional[int] = None
    match_reasons: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    resume_alignment_level: Optional[str] = None
    why_this_job_fits: Optional[str] = None


class JobResponse(BaseModel):
    jobs: List[JobPost] = []


# --------------------------------------------------------------------------- #
# 7️⃣  Site enum
# --------------------------------------------------------------------------- #
class Site(str, Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    ZIP_RECRUITER = "zip_recruiter"
    GLASSDOOR = "glassdoor"
    GOOGLE = "google"
    NAUKRI = "naukri"
    REMOTE_ROCKETSHIP = "remote_rocketship"


# --------------------------------------------------------------------------- #
# 8️⃣  Salary source (when a job contains its own compensation)
# --------------------------------------------------------------------------- #
class SalarySource(str, Enum):
    DIRECT_DATA = "direct_data"
    DESCRIPTION = "description"


# --------------------------------------------------------------------------- #
# 9️⃣  Input to the scraper
# --------------------------------------------------------------------------- #
class ScraperInput(BaseModel):
    site_type: List[Site]
    search_term: Optional[str] = None
    google_search_term: Optional[str] = None

    location: Optional[str] = None
    country: Country = Country.USA
    distance: Optional[int] = None
    is_remote: bool = False
    job_type: Optional[JobType] = None
    easy_apply: Optional[bool] = None
    offset: int = 0
    linkedin_fetch_description: bool = False
    linkedin_company_ids: Optional[List[int]] = None
    description_format: DescriptionFormat = DescriptionFormat.MARKDOWN

    results_wanted: int = 15
    hours_old: Optional[int] = None


# --------------------------------------------------------------------------- #
# 1️⃣0️⃣  Base scraper interface
# --------------------------------------------------------------------------- #
class Scraper:
    def __init__(self, site: Site, proxies=None, ca_cert=None):
        self.site = site
        self.proxies = proxies
        self.ca_cert = ca_cert

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        raise NotImplementedError