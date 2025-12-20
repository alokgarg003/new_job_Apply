# JobSpy — Personalized Job Intelligence for Alok Garg 🚀

A concise step-by-step introduction to run and extend the Alok Garg personalization pipeline. This document explains how discovery (listing URLs) and enrichment (full job scraping + resume-aware scoring) work, where outputs and logs are written, and how to customize the process.

---

## Quick summary (what the system does)
- Phase 1 — Discovery: scrape job listing URLs from Indeed, LinkedIn, Google, Naukri, ZipRecruiter and new placeholder sites (Dice, Wellfound, RemoteOK, WeWorkRemotely, RemoteRocketship). Note: the new site modules are placeholders and may require Playwright or proxy configuration for production use.
- Phase 2 — Enrichment: fetch each job page, extract skills/experience/indicators, and score the job against Alok Garg's resume using a transparent evaluator.
- Output: recruiter-ready CSV with match score, reasons, and missing skills to support application decisions.

---

## Step-by-step run guide ✅
1. Install dependencies (if not already):
   - pip install -r requirements.txt  (or use `pyproject.toml` + poetry)

2. Quick discovery (see what listings are found):
   - python run_discover.py
   - Output: printed list of discovered job URLs and metadata

3. Enrich & debug single-run (shows per-job score/reasons):
   - python run_enrich_debug.py
   - Useful for debugging specific job pages and tuning evaluation rules

4. Full personalized pipeline (discovery → enrichment → CSV):
   - python run_alok.py
   - Output files:
     - `alok_personalized.csv` — final recruiter-ready output
     - `alok_personalized_debug_<timestamp>.csv` — full enrichment dump (HTML + internals); files include timestamps to avoid accidental overwrites

5. Finalize / format (if needed):
   - python finalize_alok_output.py  (creates a nicely named final CSV if you used debug dump)

---

## Output columns (what you get in `alok_personalized.csv`) 🧾
- Job Title
- Company
- Location
- Site (Indeed / LinkedIn)
- Job URL
- Experience Range
- Key Skills Extracted
- Match Score (0–100)
- Why This Job Fits Alok Garg (human-readable reasons)
- Missing Skills (gaps vs resume)
- Resume Alignment Level (Strong Match / Good Match / Stretch Role / Ignore)

---

## Key files (what to edit / where things live) 🗂️
- `jobspy/pipeline.py` — discovery + enrichment pipeline
- `jobspy/evaluator.py` — `ProfileMatchEvaluator` scoring logic (tune weights/keywords here)
- `jobspy/model.py` — `JobPost` (extended with enrichment fields)
- `run_discover.py`, `run_enrich_debug.py`, `run_alok.py`, `finalize_alok_output.py` — convenience runners

---

## Troubleshooting & common fixes ⚠️
- 403 errors or blocked sites: try rotating/residential proxies, browser-like headers, or use Playwright/Selenium for JS-heavy pages.
- Long fetches / hangs: enrichment uses short timeouts; increase the timeout in `enrich_job` only if needed.
- PermissionError writing CSV: close any program (Excel) holding the file or change the output filename — fallback attempts are already implemented.
- False positives/negatives in matching: tweak `EXCLUDE_SIGNALS`, `PRIMARY_SKILLS`, and scoring rules in `jobspy/evaluator.py`.

## Site coverage verification (2025-12-20) 🔎
Summary of discovery checks using the default keywords (Application Support variants) and `location='India'`.

- LinkedIn — OK ✅: returned ~10 listings and enrichment works end-to-end; appears in output CSVs.
- Naukri — OK ✅: returned ~10 listings and enrichment works; `work_from_home_type` and `is_remote` are available for some jobs.
- Wellfound / Dice / Remote boards — Placeholder: modules present but not fully implemented. Use Playwright or rotating proxies for sites that block bots; full scrapers will be implemented on request.
- Glassdoor — Blocked / flaky ❌: known to use anti-bot measures; use Playwright/proxies for reliable scraping.
- ZipRecruiter — No results for India ❌: ZipRecruiter primarily returns US/CA jobs; try `location='United States'` or use ZipRecruiter API for better coverage.
- Google Jobs — No results for current combined query ❌: try simplified queries or different region; Google scraping is cursor-based and brittle for some queries.
- Indeed — No results for these India-scoped queries ❌: try adjusting `location` or role synonyms; Indeed's region behavior varies by locale.

Notes & next steps:
- If you need Glassdoor or other blocked sites, add a Playwright mode or proxy layer and enable those scrapers explicitly.
- To capture ZipRecruiter and Google coverage, re-run discovery with `location='United States'` (or region-specific queries) and/or simplify the {QUERY}.
- Consider adding scrapers for Dice and Wellfound if those platforms are important for your workflows (they are not currently implemented in this repo).
- The pipeline logs `Remote` and `Work From Home Type` where available — verify them via the debug dump (`*_debug.csv`) after runs.

---

## Tips for extension & production use ✨
- Add unit tests for `ProfileMatchEvaluator` using representative job descriptions.
- Add a CLI flag (`--min-score`) to filter output by match threshold before writing CSV.
- Consider scheduling runs (cron/airflow) and persisting outputs to a database for long-term tracking.

---

If you'd like, I can add:
- a small CLI wrapper for `run_alok.py` with `--min-score` and `--output` flags,
- unit tests for the evaluator, or
- Playwright mode for tougher sites.

Tell me which option you prefer and I’ll implement it next. ✨