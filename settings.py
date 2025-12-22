# settings.py
from pathlib import Path
from datetime import timedelta
from enum import Enum

# ---------- General ----------
RESULTS_WANTED = 150
DESCRIPTION_FORMAT = "markdown"          # "markdown" or "html"
ENFORCE_ANNUAL_SALARY = False
VERBOSE = 2

# ---------- Sites ----------
# Only the two job boards you want
SITES = ["linkedin", "naukri"]

# ---------- Location ----------
DEFAULT_LOCATION = "India"
DEFAULT_COUNTRY = "india"                # will be mapped to Country.INDIA
DEFAULT_IS_REMOTE = False
DEFAULT_DISTANCE = None                  # None = use default from scraper
DEFAULT_HOURS_OLD = None                 # None = no time filter

# ---------- LinkedIn ----------
LI_DELAY = 3.0
LI_BAND_DELAY = 4.0
LI_JOBS_PER_PAGE = 25
LI_MAX_PAGES = 40
LI_FETCH_DESCRIPTION = True
LI_EASY_APPLY = None

# ---------- Naukri ----------
NAUKRI_DELAY = 2.5
NAUKRI_BAND_DELAY = 3.5
NAUKRI_JOBS_PER_PAGE = 20
NAUKRI_MAX_PAGES = 50

# ---------- Profile (Alok‑specific) ----------
PROFILE_PRIMARY_SKILLS = [
    "linux", "shell", "bash", "servicenow", "itil", "incident", "sla",
    "mft", "sftp", "ftps", "ftp", "as2", "goanywhere", "fms", "ftg",
    "monitor", "monitoring", "alert", "log", "log analysis", "python",
    "jenkins", "bitbucket", "azure", "aws",
]

PROFILE_SECONDARY_SKILLS = [
    "java", "spring", "rest", "api", "devops", "observability",
    "grafana", "prometheus",
]

PROFILE_EXCLUDE_SIGNALS = [
    "frontend", "react", "vue", "angular", "ux", "ui",
    "dsa", "competitive programming",
]

# Evaluation weights (tweak as needed)
EVAL_PRIMARY_WEIGHT = 12
EVAL_SECONDARY_WEIGHT = 5
EVAL_MFT_BONUS = 10
EVAL_ONCALL_BONUS = 7
EVAL_CLOUD_BONUS = 5
EVAL_SUPPORT_BONUS = 6
EVAL_DEV_PENALTY = 30
PROFILE_MIN_SCORE = 45

# ---------- Output ----------
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_CSV_TEMPLATE = OUTPUT_DIR / "debug_{timestamp}.csv"
FINAL_CSV_TEMPLATE = OUTPUT_DIR / "jobs_{timestamp}.csv"

# ---------- Proxy / TLS ----------
PROXIES = None            # e.g. ["http://user:pass@host:port"]
CA_CERT = None            # path to custom CA bundle if needed

# ---------- Run modes ----------
DRY_RUN = False           # If True, use mock scrapers that do not make network calls
SAMPLE_RESULTS = 1        # Number of sample results returned in dry-run mode

# ---------- Aggregation ----------
ENABLE_AGGREGATE_OUTPUT = True
AGGREGATE_CSV = OUTPUT_DIR / "all_jobs.csv"  # master CSV storing aggregated results
AGGREGATE_DEDUPE_ON = ["job_url", "id"]
AGGREGATE_KEEP_STRATEGY = "latest"  # "latest" or "best_score"