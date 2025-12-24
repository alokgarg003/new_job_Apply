"""Playwright-based LinkedIn contact extractor (stealth + proxy support)

Usage:
  python linkedin_contact_extractor_playwright.py --input removed_scripts/test_connections_100.csv --url-column URL --output-dir outputs --batch-size 10 --headless --single-driver

Notes:
- Requires `playwright` package and browsers installed (`playwright install`).
- Provide LINKEDIN_USER and LINKEDIN_PASS in env vars for authenticated runs.
- This is a fallback option intended to be more stealthy than raw Selenium.
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


try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


from jobspy.providers import Provider, register_provider
from jobspy.providers import get_provider  # type: ignore


DEFAULT_BATCH_SIZE = 100
DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 10


def parse_contact_html(html: str):
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
    # basic regex checks
    import re
    _email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    _phone_re = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
    if not email:
        m = _email_re.search(text)
        if m:
            email = m.group(0)
    if not phone:
        m = _phone_re.search(text)
        if m:
            phone = m.group(1)
    return {"linkedin": linkedin, "website": website, "phone": phone, "email": email, "connected_since": connected_since}


@register_provider
class PlaywrightProvider(Provider):
    name = "playwright"

    def fetch_contacts(self, input_csv: str, options: Dict[str, Optional[object]] = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available in this environment")
        if options is None:
            options = {}
        headless = bool(options.get("headless", True))
        single_driver = bool(options.get("single_driver", False))
        proxy = options.get("proxy")
        url_column = options.get("url_column", "URL")
        timeout = int(options.get("timeout", DEFAULT_TIMEOUT))
        delay = float(options.get("delay", DEFAULT_DELAY))

        df = pd.read_csv(input_csv)
        if url_column not in df.columns:
            raise ValueError(f"Input CSV must contain column '{url_column}'")
        urls = [u.strip() for u in df[url_column].dropna().tolist()]

        public_rows = []
        private_rows = []

        from jobspy.playwright_pool import PlaywrightPool

        proxies_list = []
        if options.get("proxies"):
            # accept comma-separated string or list
            if isinstance(options.get("proxies"), str):
                proxies_list = [p.strip() for p in options.get("proxies").split(',') if p.strip()]
            elif isinstance(options.get("proxies"), list):
                proxies_list = [str(p).strip() for p in options.get("proxies") if p]

        pool_size = int(options.get("pool_size", 1) or 1)
        user_agent = options.get("user_agent")

        pool = PlaywrightPool(p, browser_name='chromium', proxies=proxies_list, pool_size=pool_size, headless=headless, user_agent=user_agent, timeout=timeout * 1000)

        # perform login across all contexts so pages have authenticated sessions
        username = os.environ.get("LINKEDIN_USER")
        password = os.environ.get("LINKEDIN_PASS")
        if not username or not password:
            pool.close()
            raise RuntimeError("Set LINKEDIN_USER and LINKEDIN_PASS env vars for authenticated runs")
        pool.login_all(username, password)

        # proceed per profile, borrowing pages from pool
        for profile_url in urls:
            contact_url = profile_url.rstrip('/') + "/overlay/contact-info/"
            try:
                page, idx = pool.get_page()
                page.goto(contact_url, timeout=timeout * 1000)
                # wait for contact info selector
                page.wait_for_selector("a[href^='mailto:'], a[href^='tel:'], .pv-contact-info", timeout=timeout * 1000)
                html = page.content()
                parsed = parse_contact_html(html)
                parsed['profile_url'] = profile_url
                public_rows.append(parsed)
            except PlaywrightTimeout:
                # capture snippet and cookies
                try:
                    snippet = (page.content()[:500] + '...') if len(page.content()) > 500 else page.content()
                except Exception:
                    snippet = '<no-snippet>'
                private_rows.append({"profile_url": profile_url, "reason": "timeout_or_blocked", "snippet": snippet, "proxy": pool.pages[idx].get('proxy')})
                # mark this proxy as bad for the pool
                pool.mark_bad(idx)
            except Exception as exc:
                private_rows.append({"profile_url": profile_url, "reason": f"exception_{str(exc)[:120]}"})
            time.sleep(delay + random.random() * 0.2)

        # cleanup
        try:
            pool.close()
        except Exception:
            pass

        return public_rows, private_rows


# CLI wrapper

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--url-column", default="URL")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--single-driver", action="store_true")
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(args.output_dir, f"linkedin_contact_extractor_playwright_{ts}.log")
    os.makedirs(args.output_dir, exist_ok=True)
    logger = logging.getLogger("linkedin_playwright")
    fh = logging.FileHandler(logfile, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)

    provider = PlaywrightProvider()
    public_rows, private_rows = provider.fetch_contacts(args.input, {"headless": args.headless, "single_driver": args.single_driver, "proxy": args.proxy, "url_column": args.url_column, "delay": args.delay, "timeout": args.timeout})

    # write checkpoints
    pub_path = os.path.join(args.output_dir, "public_batch_0000.csv")
    priv_path = os.path.join(args.output_dir, "private_batch_0000.csv")
    import pandas as pd
    pd.DataFrame(public_rows).to_csv(pub_path, index=False)
    pd.DataFrame(private_rows).to_csv(priv_path, index=False)
    logger.info("Playwright run complete: public=%d private=%d", len(public_rows), len(private_rows))


if __name__ == "__main__":
    cli()
