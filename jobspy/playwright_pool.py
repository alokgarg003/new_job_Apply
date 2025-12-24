"""Playwright session pool with proxy assignment and lightweight rotation.

This provides a simple pool of Playwright contexts/pages that can be used
concurrently or sequentially to distribute requests across multiple proxies.
It supports marking a page/proxy as "bad" and removing it from the pool.
"""
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger("jobspy.playwright_pool")


class PlaywrightPool:
    def __init__(self, p, browser_name: str = "chromium", proxies: Optional[List[str]] = None, pool_size: int = 1, headless: bool = True, user_agent: Optional[str] = None, timeout: int = 10000):
        self.playwright = p
        self.browser_name = browser_name
        self.pool_size = max(1, int(pool_size or 1))
        self.proxies = proxies or []
        self.pages = []  # list of dicts: {browser, context, page, proxy}
        self.next_idx = 0
        self.timeout = timeout
        self.user_agent = user_agent

        Browser = getattr(p, browser_name)
        for i in range(self.pool_size):
            proxy = self.proxies[i % len(self.proxies)] if self.proxies else None
            try:
                browser = Browser.launch(headless=headless, proxy={"server": proxy} if proxy else None)
                context = browser.new_context(user_agent=self.user_agent)
                # basic stealth
                try:
                    context.add_init_script("() => { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); }")
                except Exception:
                    pass
                page = context.new_page()
                page.set_default_timeout(self.timeout)
                self.pages.append({"browser": browser, "context": context, "page": page, "proxy": proxy})
            except Exception as exc:
                logger.exception("Failed to start pool member %d (proxy=%s): %s", i, proxy, exc)

        if not self.pages:
            raise RuntimeError("No playable pages available in pool")

    def login_all(self, username: str, password: str, login_selector: str = "#global-nav-search"):
        """Login once on each page so every context has an authenticated session."""
        for member in self.pages:
            page = member["page"]
            try:
                page.goto("https://www.linkedin.com/login")
                page.fill('input#username', username)
                page.fill('input#password', password)
                page.click('button[type=submit]')
                page.wait_for_selector(login_selector, timeout=self.timeout)
                logger.info("Logged in on proxy=%s", member.get("proxy"))
            except Exception as exc:
                logger.exception("Login failed for proxy=%s: %s", member.get("proxy"), exc)

    def get_page(self) -> Tuple[object, int]:
        """Round-robin borrow a page and return (page, idx)."""
        if not self.pages:
            raise RuntimeError("No pages available in pool")
        idx = self.next_idx % len(self.pages)
        self.next_idx += 1
        return self.pages[idx]["page"], idx

    def mark_bad(self, idx: int):
        """Remove a page at idx from the pool (close its context)"""
        if 0 <= idx < len(self.pages):
            m = self.pages.pop(idx)
            try:
                m["context"].close()
                m["browser"].close()
            except Exception:
                pass
            logger.warning("Removed bad proxy/page at idx=%d (proxy=%s). Remaining=%d", idx, m.get("proxy"), len(self.pages))

    def close(self):
        for m in list(self.pages):
            try:
                m["context"].close()
            except Exception:
                pass
            try:
                m["browser"].close()
            except Exception:
                pass
        self.pages = []
