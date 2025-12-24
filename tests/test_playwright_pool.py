import pytest


@pytest.mark.skipif(not pytest.importorskip('playwright'), reason='Playwright not available')
def test_create_pool_and_login():
    from playwright.sync_api import sync_playwright
    from jobspy.playwright_pool import PlaywrightPool
    with sync_playwright() as p:
        pool = PlaywrightPool(p, pool_size=1, headless=True)
        assert len(pool.pages) == 1
        # can't actually login in CI environment, but ensure close works
        pool.close()
