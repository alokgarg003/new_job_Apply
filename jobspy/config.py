# jobspy/config.py
"""
Enhanced configuration management with validation and environment-specific settings.
"""
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import os


class DatabaseConfig(BaseModel):
    url: str = Field(..., env="SUPABASE_URL")
    anon_key: str = Field(..., env="SUPABASE_ANON_KEY")
    service_role_key: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")

    @classmethod
    def from_env(cls):
        return cls(
            url=os.getenv("SUPABASE_URL", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )


class ScraperConfig(BaseModel):
    linkedin_delay: float = 3.0
    linkedin_band_delay: float = 4.0
    linkedin_jobs_per_page: int = 25
    linkedin_max_pages: int = 40
    linkedin_fetch_description: bool = True

    naukri_delay: float = 2.5
    naukri_band_delay: float = 3.5
    naukri_jobs_per_page: int = 20
    naukri_max_pages: int = 50

    default_results_wanted: int = 150
    description_format: str = "markdown"

    proxies: Optional[List[str]] = None
    ca_cert: Optional[str] = None


class MatchingConfig(BaseModel):
    primary_skills: List[str] = [
        "linux", "shell", "bash", "python", "jenkins", "bitbucket",
        "azure", "aws", "terraform", "ci_cd", "automation", "cloudops",
        "monitoring", "alerting", "log_analysis", "network_fundamentals",
        "mft", "sftp", "ftps", "ftp", "as2", "goanywhere", "fms", "ftg",
        "servicenow", "itil", "incident_management", "sla_management"
    ]

    secondary_skills: List[str] = [
        "java", "spring boot", "rest api", "microservices", "docker", "kubernetes",
        "observability", "grafana", "prometheus", "databricks", "spark"
    ]

    exclude_signals: List[str] = [
        "frontend", "react", "vue", "angular", "ux", "ui",
        "dsa", "competitive programming", "html", "css"
    ]

    primary_weight: int = 12
    secondary_weight: int = 5
    mft_bonus: int = 10
    oncall_bonus: int = 7
    cloud_bonus: int = 5
    support_bonus: int = 6
    dev_penalty: int = 30
    min_score: int = 45


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 3600
    max_size: int = 1000


class AppConfig(BaseModel):
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    database: DatabaseConfig
    scraper: ScraperConfig = ScraperConfig()
    matching: MatchingConfig = MatchingConfig()
    cache: CacheConfig = CacheConfig()

    output_dir: Path = Field(default=Path("outputs"))

    @validator("output_dir", pre=True)
    def ensure_output_dir(cls, v):
        p = Path(v) if not isinstance(v, Path) else v
        p.mkdir(parents=True, exist_ok=True)
        return p

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or initialize application configuration."""
    global _config
    if _config is None:
        _config = AppConfig(
            database=DatabaseConfig.from_env(),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    return _config


def reset_config():
    """Reset configuration (useful for testing)."""
    global _config
    _config = None
