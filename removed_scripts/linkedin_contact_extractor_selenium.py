"""
Selenium-based LinkedIn contact extractor

Usage:
  python linkedin_contact_extractor_selenium.py \
    --input Connections1.csv --url-column URL --output-dir outputs \
    --batch-size 200 --workers 4 --headless --retries 3 --delay 0.5

Setup:
- Set LINKEDIN_USER and LINKEDIN_PASS in environment variables, or create a local config file (not recommended).
- Install dependencies: pip install -r requirement.txt selenium webdriver-manager pandas beautifulsoup4 openpyxl

Behavior:
- Logs in with Selenium using a primary driver, extracts cookies, and spins up worker drivers that reuse those cookies.
- Each worker navigates to profile_url + "/overlay/contact-info/", waits for overlay selectors, extracts contact info.
- Checkpoints per-batch CSVs are written so runs can resume.
- Final outputs are timestamped Excel files (CSV fallback).

Notes & security:
- Do NOT hardcode credentials in the repo. Use environment variables.
- Running many logged-in requests may violate LinkedIn terms; use responsibly and with permission.
"""

import argparse
import logging
import os
import time
import random
from datetime import datetime
from typing import Optional, Dict, Tuple, List

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# ---------- Defaults ----------
DEFAULT_BATCH_SIZE = 200
DEFAULT_WORKERS = 4
DEFAULT_DELAY = 0.5
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 10
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# --------- Utilities ----------

def setup_logging(logfile: str):
    logger = logging.getLogger("linkedin_selenium")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger


from selenium.webdriver.chrome.service import Service

def make_driver(headless: bool, user_agent: str = DEFAULT_USER_AGENT, proxy: Optional[str] = None):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    # reduce detection surface
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # optional proxy
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    # instantiate driver using Service object to avoid positional conflicts
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Make navigator.webdriver less detectable (via CDP) when supported
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
    except Exception:
        # not critical; proceed
        pass

    return driver


def login_linkedin(driver, username: str, password: str, timeout: int = 20) -> bool:
    logger = logging.getLogger("linkedin_selenium")
    try:
        driver.get("https://www.linkedin.com/login")
        wait = WebDriverWait(driver, timeout)
        user_el = wait.until(EC.presence_of_element_located((By.ID, "username")))
        pass_el = driver.find_element(By.ID, "password")
        user_el.clear(); user_el.send_keys(username)
        pass_el.clear(); pass_el.send_keys(password)
        pass_el.submit()
        # wait for top-level element indicating logged in
        wait.until(EC.presence_of_element_located((By.ID, "global-nav-search")))
        logger.info("Logged into LinkedIn as %s", username)
        return True
    except Exception as exc:
        logger.exception("Login failed: %s", exc)
        return False


def cookies_from_driver(driver) -> List[dict]:
    # Return cookies in format Selenium cookies
    return driver.get_cookies()


def apply_cookies_to_driver(driver, cookies: List[dict], domain: str = "https://www.linkedin.com"):
    """Apply cookies from primary to worker driver, preserving useful attributes and refreshing the page to activate them."""
    driver.get(domain)
    for c in cookies:
        cookie = {
            "name": c.get("name"),
            "value": c.get("value"),
            "path": c.get("path", "/"),
            "domain": c.get("domain", ".linkedin.com"),
        }
        if "expiry" in c and c.get("expiry") is not None:
            try:
                cookie["expiry"] = int(c["expiry"])
            except Exception:
                pass
        if c.get("secure"):
            cookie["secure"] = bool(c.get("secure"))
        if c.get("httpOnly"):
            cookie["httpOnly"] = bool(c.get("httpOnly"))
        try:
            driver.add_cookie(cookie)
        except WebDriverException:
            logging.getLogger("linkedin_selenium").debug("Failed to add cookie %s (skipping)", cookie.get("name"))
            continue
    # refresh to make cookies active
    try:
        driver.get(domain)
    except Exception:
        pass


# ---------- Parsing helpers (soup fallback) ----------
import re
_email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_phone_re = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
_date_re = re.compile(r"(\b\w+\s*(?:\d{1,2},\s*)?\d{4}\b)")


def parse_contact_html(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    linkedin = None
    website = None
    phone = None
    email = None
    connected_since = None

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("mailto:") and not email:
            email = href.split("mailto:", 1)[1].split("?")[0]
        if href.startswith("tel:") and not phone:
            phone = href.split("tel:", 1)[1]
        if href.startswith("http") and "linkedin.com" not in href and not website:
            website = href
        if "linkedin.com/in" in href and not linkedin:
            linkedin = href

    text = soup.get_text(separator=" \n ", strip=True)
    if not email:
        m = _email_re.search(text)
        if m:
            email = m.group(0)
    if not phone:
        m = _phone_re.search(text)
        if m:
            phone = re.sub(r"\s+", " ", m.group(1)).strip()
    low = text.lower()
    if "connected since" in low:
        m = re.search(r"connected since[:]?\s*([A-Za-z0-9,\s]+)", low)
        if m:
            connected_since = m.group(1).strip()
    else:
        m = _date_re.search(text)
        if m:
            connected_since = m.group(1)

    return {"linkedin": linkedin, "website": website, "phone": phone, "email": email, "connected_since": connected_since}


# ---------- Worker: fetch overlay using Selenium ----------

def fetch_overlay(driver, contact_url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, Optional[str], Optional[str]]:
    """Return (success, html, reason)"""
    logger = logging.getLogger("linkedin_selenium")
    try:
        driver.get(contact_url)
        wait = WebDriverWait(driver, timeout)
        # Wait: the contact overlay may present anchors like mailto or a container with class 'pv-contact-info'
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='mailto:'], a[href^='tel:'], .pv-contact-info")))
        except TimeoutException:
            # Overlay may not load; capture diagnostic info
            body = driver.page_source
            snippet = (body[:500] + '...') if len(body) > 500 else body
            cookie_count = len(driver.get_cookies()) if hasattr(driver, 'get_cookies') else 0
            logger.debug("Fetch timeout for %s — title=%s cookies=%d snippet=%s", contact_url, getattr(driver, 'title', '<no-title>'), cookie_count, snippet)
            low = body.lower()
            if "login" in low or "sign in" in low:
                return False, None, "login_required"
            if "verify" in low or "unusual activity" in low or "blocked" in low:
                return False, None, "blocked_by_site"
            return False, None, "timeout_or_no_content"
        html = driver.page_source
        return True, html, None
    except Exception as exc:
        logger.exception("Selenium error fetching %s: %s", contact_url, exc)
        return False, None, str(exc)


# ---------- Checkpointing / saving ----------

def write_batch_checkpoint(output_dir: str, batch_idx: int, public_rows: List[dict], private_rows: List[dict]):
    os.makedirs(output_dir, exist_ok=True)
    pub_path = os.path.join(output_dir, f"public_batch_{batch_idx:04d}.csv")
    priv_path = os.path.join(output_dir, f"private_batch_{batch_idx:04d}.csv")
    pd.DataFrame(public_rows).to_csv(pub_path, index=False)
    pd.DataFrame(private_rows).to_csv(priv_path, index=False)
    logging.getLogger("linkedin_selenium").info("Wrote batch checkpoints %s and %s", pub_path, priv_path)


def finalize_outputs(output_dir: str):
    # combine batch CSVs and save final Excel or CSV fallback
    final_public_cols = ["profile_url", "linkedin", "website", "phone", "email", "connected_since"]
    final_private_cols = ["profile_url", "reason"]
    pubs = []
    privs = []
    for f in sorted(os.listdir(output_dir)):
        path = os.path.join(output_dir, f)
        if f.startswith("public_batch_") and f.endswith(".csv"):
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    pubs.append(df)
            except Exception:
                continue
        if f.startswith("private_batch_") and f.endswith(".csv"):
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    privs.append(df)
            except Exception:
                continue
    public_df = pd.concat(pubs, ignore_index=True) if pubs else pd.DataFrame(columns=final_public_cols)
    private_df = pd.concat(privs, ignore_index=True) if privs else pd.DataFrame(columns=final_private_cols)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pub_xlsx = os.path.join(output_dir, f"public_profiles_{ts}.xlsx")
    priv_xlsx = os.path.join(output_dir, f"private_profiles_{ts}.xlsx")
    pub_csv = os.path.join(output_dir, f"public_profiles_{ts}.csv")
    priv_csv = os.path.join(output_dir, f"private_profiles_{ts}.csv")
    try:
        public_df.to_excel(pub_xlsx, index=False)
        private_df.to_excel(priv_xlsx, index=False)
        return pub_xlsx, priv_xlsx, len(public_df), len(private_df)
    except Exception as exc:
        logging.getLogger("linkedin_selenium").warning("Excel save failed (%s). Falling back to CSV.", exc)
        public_df.to_csv(pub_csv, index=False)
        private_df.to_csv(priv_csv, index=False)
        return pub_csv, priv_csv, len(public_df), len(private_df)


# ---------- Main orchestration ----------

def process_with_selenium(input_csv: str, url_column: str, output_dir: str, batch_size: int, workers: int, headless: bool, retries: int, delay: float, timeout: int, proxy: Optional[str], single_driver: bool = False):
    logger = logging.getLogger("linkedin_selenium")
    df = pd.read_csv(input_csv)
    if url_column not in df.columns:
        raise ValueError(f"Input CSV must contain column '{url_column}'")
    urls = [u.strip() for u in df[url_column].tolist() if str(u).strip()]

    username = os.environ.get("LINKEDIN_USER")
    password = os.environ.get("LINKEDIN_PASS")
    if not username or not password:
        raise RuntimeError("Please set LINKEDIN_USER and LINKEDIN_PASS environment variables for authenticated runs")

    logger.info("Starting authenticated run: headless=%s workers=%d single_driver=%s", headless, workers, single_driver)

    # primary driver: login and capture cookies
    primary = make_driver(headless=headless, proxy=proxy)
    try:
        if not login_linkedin(primary, username, password, timeout=timeout):
            raise RuntimeError("Login failed; aborting")
        cookies = cookies_from_driver(primary)
    except Exception:
        primary.quit()
        raise

    # If using single_driver mode, we'll use the primary driver for fetching; otherwise create workers per batch

    total = len(urls)
    batch_idx = 0
    processed = 0

    for i in range(0, total, batch_size):
        batch = urls[i:i+batch_size]
        public_rows = []
        private_rows = []
        logger.info("Processing batch %d (size=%d)", batch_idx + 1, len(batch))

        # create worker drivers and apply cookies (or use single primary driver)
        workers_drivers = []
        if single_driver:
            workers_drivers = [primary]
        else:
            for _ in range(min(workers, len(batch))):
                d = make_driver(headless=headless, proxy=proxy)
                apply_cookies_to_driver(d, cookies)
                # verify that cookies are present
                try:
                    ck_count = len(d.get_cookies())
                except Exception:
                    ck_count = 0
                if ck_count == 0:
                    logger.warning("Worker driver has 0 cookies after apply — possible cookie transfer issue")
                workers_drivers.append(d)

        # distribute work among worker drivers sequentially (each driver handles multiple profiles)
        try:
            for idx, profile_url in enumerate(batch):
                d = workers_drivers[idx % len(workers_drivers)]
                contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
                attempt = 0
                while attempt <= retries:
                    success, html, reason = fetch_overlay(d, contact_url, timeout=timeout)
                    if success and html:
                        parsed = parse_contact_html(html)
                        parsed["profile_url"] = profile_url
                        public_rows.append(parsed)
                        logger.info("Parsed %s", profile_url)
                        break
                    else:
                        attempt += 1
                        logger.debug("Failed %s attempt %d/%d: %s", profile_url, attempt, retries, reason)
                        if attempt > retries:
                            private_rows.append({"profile_url": profile_url, "reason": reason or "unavailable"})
                            break
                        # backoff before retry
                        sleep_for = (2 ** attempt) * delay + random.random() * 0.5
                        time.sleep(sleep_for)
                processed += 1
                if processed % 50 == 0:
                    logger.info("Processed %d / %d", processed, total)
                # polite per-profile delay
                time.sleep(delay + random.random() * 0.2)
        finally:
            # quit worker drivers for this batch (but not the primary if single_driver)
            for wd in workers_drivers:
                if single_driver and wd is primary:
                    continue
                try:
                    wd.quit()
                except Exception:
                    pass

        # checkpoint
        write_batch_checkpoint(output_dir, batch_idx, public_rows, private_rows)
        batch_idx += 1
        # small pause between batches
        time.sleep(max(1.0, delay))

    primary.quit()

    pub_path, priv_path, pub_count, priv_count = finalize_outputs(output_dir)
    summary = {"total": total, "public_count": pub_count, "private_count": priv_count, "public_path": pub_path, "private_path": priv_path}
    logger.info("Run complete: %s", summary)
    return summary


# ---------- CLI ----------

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--url-column", default="profile_url")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--single-driver", action="store_true", dest="single_driver", help="Use primary driver for all fetches (no worker drivers)")

    args = parser.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(args.output_dir, f"linkedin_contact_extractor_selenium_{ts}.log")
    os.makedirs(args.output_dir, exist_ok=True)
    logger = setup_logging(logfile)

    try:
        summary = process_with_selenium(args.input, args.url_column, args.output_dir, args.batch_size, args.workers, args.headless, args.retries, args.delay, args.timeout, args.proxy, single_driver=args.single_driver)
        logger.info("Finished run. Summary: %s", summary)
    except Exception as exc:
        logger.exception("Processing failed: %s", exc)
        raise


if __name__ == "__main__":
    cli()
