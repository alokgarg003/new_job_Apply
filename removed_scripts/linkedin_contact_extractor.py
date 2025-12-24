"""
LinkedIn contact extractor (enhanced)

This script is designed to process large CSVs of LinkedIn profile URLs (e.g., ~4k rows)
and attempt to fetch the public contact overlay at `/overlay/contact-info/` for each
profile without logging in.

Features added:
- Batch processing with configurable batch size
- Concurrency via ThreadPoolExecutor (configurable workers)
- Retry with exponential backoff and jitter
- Optional proxy support and rate-limiting (per-request delay)
- Checkpointing: write per-batch CSV checkpoints so runs can resume and partial results are retained
- Final output saved as Excel (if available) or CSV fallback
- Summary report and robust logging

Usage example:
  python linkedin_contact_extractor.py --input Connections1.csv --url-column URL --output-dir outputs --batch-size 200 --workers 8 --retries 3 --delay 0.4

Requirements: pandas, requests, beautifulsoup4, openpyxl (optional for Excel output)
"""
import argparse
import logging
import os
import random
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, List
import math

import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------- Configurable defaults ----------
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RETRIES = 2
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_BATCH_SIZE = 200
DEFAULT_WORKERS = 8
DEFAULT_DELAY = 0.5  # delay between requests (seconds)
DEFAULT_BACKOFF_FACTOR = 1.5


# ---------- Fetching / network ----------

def fetch_profile(session: requests.Session, url: str, headers: dict, timeout: int, retries: int, backoff_factor: float, delay: float, proxies: Optional[dict]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Fetch profile overlay content using an existing session.

    Returns (status_code, text, reason). Retries with exponential backoff + jitter.
    """
    attempt = 0
    while attempt <= retries:
        try:
            if delay and attempt == 0:
                # small polite delay before first try
                time.sleep(delay + random.random() * 0.1)
            resp = session.get(url, headers=headers, timeout=timeout, proxies=proxies)
            status = resp.status_code
            text = resp.text or ""
            # Consider 2xx and non-empty content as success
            if 200 <= status < 300 and len(text) > 50:
                # check for login gate
                low = text.lower()
                if "login" in low or "sign in" in low or "accessed via a browser" in low:
                    return status, text, "login_required"
                return status, text, None
            # treat certain codes as blocked
            if status in (401, 403, 404):
                return status, text, f"HTTP {status}"
            # 999 is LinkedIn's anti-bot response in some contexts
            if status == 999:
                return status, text, "HTTP 999"
            # otherwise, treat as transient and retry
            reason = f"HTTP {status}"
            attempt += 1
            sleep_for = backoff_factor ** attempt + random.random() * 0.5
            time.sleep(sleep_for)
            continue
        except requests.RequestException as exc:
            attempt += 1
            if attempt > retries:
                return None, None, str(exc)
            time.sleep(backoff_factor ** attempt + random.random() * 0.5)
    return None, None, "max_retries_exceeded"


# ---------- Parsing ----------

import re
_email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_phone_re = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
_date_re = re.compile(r"(\b\w+\s*(?:\d{1,2},\s*)?\d{4}\b)")  # crude


def parse_contact_info(html: str) -> Dict[str, Optional[str]]:
    """Extract contact info from overlay HTML fragment.

    Returns dict with keys: linkedin, website, phone, email, connected_since
    """
    soup = BeautifulSoup(html, "html.parser")
    linkedin = None
    website = None
    phone = None
    email = None
    connected_since = None

    # anchors
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

    body_text = soup.get_text(separator=" \n ", strip=True)

    if not email:
        m = _email_re.search(body_text)
        if m:
            email = m.group(0)
    if not phone:
        m = _phone_re.search(body_text)
        if m:
            phone = re.sub(r"\s+", " ", m.group(1)).strip()

    low = body_text.lower()
    if "connected since" in low:
        m = re.search(r"connected since[:]?\s*([A-Za-z0-9,\s]+)", low)
        if m:
            connected_since = m.group(1).strip()
    else:
        m = _date_re.search(body_text)
        if m:
            connected_since = m.group(1)

    return {
        "linkedin": linkedin,
        "website": website,
        "phone": phone,
        "email": email,
        "connected_since": connected_since,
    }


# ---------- Helpers / checkpointing ----------

def chunked_iterable(iterable: List[str], chunk_size: int):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


def write_checkpoint(output_dir: str, batch_idx: int, public_rows: List[Dict], private_rows: List[Dict]):
    os.makedirs(output_dir, exist_ok=True)
    pub_path = os.path.join(output_dir, f"public_part_{batch_idx:04d}.csv")
    priv_path = os.path.join(output_dir, f"private_part_{batch_idx:04d}.csv")
    pd.DataFrame(public_rows).to_csv(pub_path, index=False)
    pd.DataFrame(private_rows).to_csv(priv_path, index=False)
    logging.getLogger("linkedin_extractor").info("Wrote checkpoints: %s, %s", pub_path, priv_path)


def combine_checkpoints(output_dir: str, final_public_cols: List[str], final_private_cols: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    pubs = []
    privs = []
    for f in sorted(os.listdir(output_dir)):
        if f.startswith("public_part_") and f.endswith(".csv"):
            pubs.append(pd.read_csv(os.path.join(output_dir, f)))
        if f.startswith("private_part_") and f.endswith(".csv"):
            privs.append(pd.read_csv(os.path.join(output_dir, f)))
    public_df = pd.concat(pubs, ignore_index=True) if pubs else pd.DataFrame(columns=final_public_cols)
    private_df = pd.concat(privs, ignore_index=True) if privs else pd.DataFrame(columns=final_private_cols)
    return public_df, private_df


def save_final_results(public_df: pd.DataFrame, private_df: pd.DataFrame, output_dir: str) -> Tuple[str, str]:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)
    pub_xlsx = os.path.join(output_dir, f"public_profiles_{ts}.xlsx")
    priv_xlsx = os.path.join(output_dir, f"private_profiles_{ts}.xlsx")
    pub_csv = os.path.join(output_dir, f"public_profiles_{ts}.csv")
    priv_csv = os.path.join(output_dir, f"private_profiles_{ts}.csv")
    try:
        public_df.to_excel(pub_xlsx, index=False)
        private_df.to_excel(priv_xlsx, index=False)
        return pub_xlsx, priv_xlsx
    except Exception as exc:
        logging.getLogger("linkedin_extractor").warning("Excel save failed (%s). Falling back to CSV.", exc)
        public_df.to_csv(pub_csv, index=False)
        private_df.to_csv(priv_csv, index=False)
        return pub_csv, priv_csv


# ---------- Main processing ----------

def process_profiles(input_csv: str, output_dir: str, user_agent: str, timeout: int, retries: int, batch_size: int, workers: int, delay: float, backoff_factor: float, url_column: str = "profile_url", proxies: Optional[dict] = None, max_profiles: Optional[int] = None) -> Dict[str, object]:
    logger = logging.getLogger("linkedin_extractor")
    df = pd.read_csv(input_csv)
    if url_column not in df.columns:
        raise ValueError(f"Input CSV must contain column '{url_column}'")

    urls = [str(x).strip() for x in df[url_column].tolist() if str(x).strip()]
    total = len(urls)
    if max_profiles:
        total = min(total, max_profiles)
        urls = urls[:total]

    logger.info("Processing %d profiles in batches of %d (workers=%d)", total, batch_size, workers)

    session = requests.Session()
    headers = {"User-Agent": user_agent}

    final_public_cols = ["profile_url", "linkedin", "website", "phone", "email", "connected_since"]
    final_private_cols = ["profile_url", "reason"]

    batch_idx = 0
    processed = 0
    for batch in chunked_iterable(urls, batch_size):
        public_rows = []
        private_rows = []
        logger.info("Starting batch %d (size=%d)", batch_idx + 1, len(batch))
        with ThreadPoolExecutor(max_workers=workers) as exe:
            futures = {}
            for profile_url in batch:
                contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
                futures[exe.submit(_fetch_and_parse_worker, session, contact_url, headers, timeout, retries, backoff_factor, delay, proxies, profile_url)] = profile_url
            for fut in as_completed(futures):
                profile_url = futures[fut]
                try:
                    success, data_or_reason = fut.result()
                    if success:
                        row = data_or_reason
                        row["profile_url"] = profile_url
                        public_rows.append({k: row.get(k) for k in final_public_cols})
                    else:
                        private_rows.append({"profile_url": profile_url, "reason": data_or_reason or "unavailable"})
                except Exception as exc:
                    logger.exception("Error processing %s: %s", profile_url, exc)
                    private_rows.append({"profile_url": profile_url, "reason": str(exc)})
                processed += 1
                if processed % 50 == 0:
                    logger.info("Processed %d / %d", processed, total)
        # write batch checkpoint
        write_checkpoint(output_dir, batch_idx, public_rows, private_rows)
        batch_idx += 1
        # polite pause between batches
        time.sleep(max(0.5, delay))

    # combine checkpoints and produce final files
    public_df, private_df = combine_checkpoints(output_dir, final_public_cols, final_private_cols)
    pub_path, priv_path = save_final_results(public_df[final_public_cols], private_df[final_private_cols], output_dir)

    summary = {
        "total": total,
        "public_count": len(public_df),
        "private_count": len(private_df),
        "public_path": pub_path,
        "private_path": priv_path,
    }
    logger.info("Done: %s", summary)
    return summary


def _fetch_and_parse_worker(session, contact_url, headers, timeout, retries, backoff_factor, delay, proxies, profile_url):
    """Worker invoked in a thread: fetch and parse single URL."""
    logger = logging.getLogger("linkedin_extractor")
    status, text, reason = fetch_profile(session, contact_url, headers=headers, timeout=timeout, retries=retries, backoff_factor=backoff_factor, delay=delay, proxies=proxies)
    if status and 200 <= status < 300 and text:
        parsed = parse_contact_info(text)
        logger.info("Parsed: %s", profile_url)
        return True, parsed
    else:
        logger.debug("Private/inaccessible: %s (%s)", profile_url, reason)
        return False, reason


# ---------- Logging setup ----------

def setup_logging(logfile: str):
    logger = logging.getLogger("linkedin_extractor")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    # avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger


# ---------- CLI ----------

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for outputs and checkpoints")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Number of retries per request")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout seconds")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    parser.add_argument("--max-profiles", type=int, default=None, help="Limit number of profiles for quick tests")
    parser.add_argument("--url-column", default="profile_url", help="Column name containing profile URLs")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Number of profiles per batch")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent worker threads")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests (seconds)")
    parser.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF_FACTOR, help="Backoff factor for retries")
    parser.add_argument("--proxy", default=None, help="Optional proxy URL (http://user:pass@host:port) or None")

    args = parser.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(args.output_dir, f"linkedin_contact_extractor_{ts}.log")
    os.makedirs(args.output_dir, exist_ok=True)
    logger = setup_logging(logfile)

    proxies = None
    if args.proxy:
        proxies = {"http": args.proxy, "https": args.proxy}

    try:
        summary = process_profiles(
            args.input,
            args.output_dir,
            args.user_agent,
            args.timeout,
            args.retries,
            args.batch_size,
            args.workers,
            args.delay,
            args.backoff,
            url_column=args.url_column,
            proxies=proxies,
            max_profiles=args.max_profiles,
        )
        logger.info("Finished run. Summary: %s", summary)
    except Exception as exc:
        logger.exception("Processing failed: %s", exc)
        raise


if __name__ == "__main__":
    cli()



def setup_logging(logfile: str):
    logger = logging.getLogger("linkedin_extractor")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input CSV with profile_url column (or specify another column with --url-column)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for timestamped Excel outputs")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Number of retries on failure")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout seconds")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    parser.add_argument("--max-profiles", type=int, default=None, help="Limit number of profiles for quick tests")
    parser.add_argument("--url-column", default="profile_url", help="Name of the column containing profile URLs (default 'profile_url')")

    args = parser.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(args.output_dir, f"linkedin_contact_extractor_{ts}.log")
    os.makedirs(args.output_dir, exist_ok=True)
    logger = setup_logging(logfile)

    try:
        stats = process_profiles(args.input, args.output_dir, args.user_agent, args.timeout, args.retries, args.max_profiles, url_column=args.url_column)
        logger.info("Done. Public: %d, Private: %d", stats["public_count"], stats["private_count"])
        logger.info("Public saved to %s", stats["public_path"])
        logger.info("Private saved to %s", stats["private_path"])
    except Exception as exc:
        logger.exception("Processing failed: %s", exc)
        raise


if __name__ == "__main__":
    cli()
