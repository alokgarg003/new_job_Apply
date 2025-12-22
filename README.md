

# JobSpy — Personalized Job Intelligence 🚀

A robust, extensible job‑scraping and matching pipeline focused on **India** with optional remote‑job exploration.  
This README walks you through the architecture, how to run it, and how to safely experiment with additional job boards without breaking your reliable sources (LinkedIn + Naukri).

## 📋 Quick Summary

- **Phase 1 — Discovery**: scrape job listing URLs from supported boards (LinkedIn, Naukri, Google, Indeed, ZipRecruiter, Glassdoor, RemoteRocketship).
- **Phase 2 — Enrichment**: fetch full job pages, extract skills/experience/indicators, and score against Alok Garg’s resume.
- **Output**: recruiter‑ready CSV with match score, reasons, missing skills, and alignment level.

## 📁 Project Structure

```
JobSpy/
├── .github/
│   └── workflows/
│       └── publish-to-pypi.yml           # CI to publish to PyPI
├── jobspy/
│   ├── __init__.py                       # Public API exports
│   ├── model.py                          # Pydantic data contracts (JobPost, ScraperInput, etc.)
│   ├── exception.py                      # Custom exceptions
│   ├── evaluator.py                      # ProfileMatchEvaluator (resume‑aware scoring)
│   ├── util.py                           # Shared utilities (session, logging, helpers)
│   ├── pipeline.py                       # Core discovery + enrichment pipeline
│   ├── scrape_jobs.py                    # Public scraping API (concurrent multi‑site)
│   ├── google/
│   │   ├── __init__.py
│   │   ├── constant.py                   # Google headers & async params
│   │   ├── util.py                       # Job‑info extraction helpers
│   │   └── google.py                     # Google Jobs scraper
│   ├── indeed/
│   │   ├── __init__.py
│   │   ├── constant.py                   # Indeed GraphQL query & headers
│   │   ├── util.py                       # Job‑type, compensation helpers
│   │   └── indeed.py                     # Indeed scraper
│   ├── linkedin/
│   │   ├── __init__.py
│   │   ├── constant.py                   # LinkedIn headers
│   │   ├── util.py                       # Job‑type, location helpers
│   │   └── linkedin.py                   # LinkedIn scraper
│   ├── naukri/
│   │   ├── __init__.py
│   │   ├── constant.py                   # Naukri headers
│   │   ├── util.py                       # Job‑type, remote helpers
│   │   └── naukri.py                     # Naukri scraper
│   ├── ziprecruiter/
│   │   ├── __init__.py
│   │   ├── constant.py                   # ZipRecruiter headers
│   │   ├── util.py                       # Job‑type, remote helpers
│   │   └── ziprecruiter.py               # ZipRecruiter scraper (blocked for India)
│   ├── glassdoor/
│   │   ├── __init__.py
│   │   ├── constant.py                   # Glassdoor headers & query
│   │   ├── util.py                       # Job‑type, compensation helpers
│   │   └── glassdoor.py                  # Glassdoor scraper (blocked for India)
│   ├── remoterocketship/
│   │   ├── __init__.py
│   │   ├── constant.py                   # RemoteRocketship headers
│   │   ├── util.py                       # Remote‑specific helpers
│   │   └── remoterocketship.py           # RemoteRocketship scraper
│   └── tests/
│       ├── 01_test_pipeline_validation.py
│       ├── 02_test_pipeline_normalize.py
│       ├── 03_test_debug_file_and_normalization.py
│       └── 04_test_write_debug_file.py
├── scripts/
│   ├── run_discover.py                   # Quick discovery (URLs only)
│   ├── run_enrich_debug.py               # Debug enrichment (per‑job scores)
│   ├── run_alok.py                       # Full personalized pipeline (default)
│   ├── run_alok_remote.py                # Include RemoteRocketship
│   └── finalize_alok_output.py           # Helper to rename debug dump
├── main.py                               # CLI entry point
├── pyproject.toml                        # Poetry config
├── requirements.txt                      # Pip requirements
├── LICENSE
└── README.md
```

## 🚀 Quick Start

### 1️⃣ Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using Poetry
poetry install
```

### 2️⃣ Run the Default Pipeline (LinkedIn + Naukri)

```bash
python run_alok.py
```

**What it does**
- Searches for jobs matching `["Application Support", "ServiceNow", "IT Support"]` in India.
- Scrapes LinkedIn and Naukri (these are known to work for India).
- Enriches each job with skill extraction and resume-aware scoring.
- Saves `alok_personalized.csv` (final) and a timestamped debug dump.

**Full run (complete job list)**

To run a full pipeline and obtain a larger results set (for example, 200 results), use either the packaged run script or the CLI:

```bash
# Packaged full run (uses 200 results by default and writes `alok_personalized.csv`)
python run_alok.py

# CLI full run with explicit results and output path
python main.py --results 200 --output outputs/full_run.csv
```

Notes:
- Aggregation: when `settings.ENABLE_AGGREGATE_OUTPUT` is True the pipeline will append results to `outputs/all_jobs.csv`.
- Completion message: the pipeline prints a summary like: `Personalized pipeline completed. X jobs saved to <output_file>`.
- Manual append to master (if needed):

```bash
python -c "from jobspy.output_manager import append_to_master; print(append_to_master('outputs/full_run.csv','outputs/all_jobs.csv'))"
```

### 3️⃣ Add Remote Jobs (Optional)

```bash
python run_alok_remote.py
```

This includes **RemoteRocketship** in addition to LinkedIn + Naukri, giving you remote opportunities without affecting your baseline.

### 4️⃣ CLI Usage

```bash
python main.py "Application Support" -l India -s linkedin naukri -r --results 50 --output my_jobs.csv
```

Available sites: `linkedin`, `indeed`, `glassdoor`, `naukri`, `google`, `ziprecruiter`.

**Tip:** For India, stick to `linkedin` and `naukri`. Other sites may return 0 jobs or be blocked.

## 📊 Output Columns

| Column | Description |
|--------|-------------|
| `title` | Job title |
| `company_name` | Employer name |
| `location` | City, State, Country |
| `site` | Source (linkedin / naukri / remote_rocketship) |
| `job_url` | Direct link to the listing |
| `experience_range` | Extracted years of experience |
| `key_skills` | Skills matched from the description |
| `match_score` | 0–100 score against your resume |
| `why_this_job_fits` | Human‑readable reasons |
| `missing_skills` | Gaps vs your resume |
| `resume_alignment_level` | Strong Match / Good Match / Stretch / Ignore |
| `is_remote` | Whether the job is remote |
| `work_from_home_type` | Remote/Hybrid/Onsite (when available) |

## 🔧 Extending & Experimenting Safely

### A. Keep Your Baseline Intact

The pipeline includes a **safe‑site filter** that only uses LinkedIn + Naukri for India. You can run any additional site without affecting this baseline by using the `--remote` flag or passing a custom site list.

### B. Try Other Sites (Optional)

If you want to experiment with Google, Indeed, ZipRecruiter, or Glassdoor:

1. **Force a US location** for those sites to see if they return remote listings:

   ```bash
   # Example: add Google with US location
   python main.py "Application Support" -l India -s linkedin naukri google --remote
   ```

   The code will automatically override the location to “United States” for Google while keeping LinkedIn + Naukri on “India”.

2. **Add a Proxy** for blocked sites (ZipRecruiter, Glassdoor):

   Edit `jobspy/enhance.py` and provide proxies:

   ```python
   def get_proxy_for_site(site):
       proxies = {
           "ziprecruiter": {"http": "YOUR_PROXY", "https": "YOUR_PROXY"},
           "glassdoor": {"http": "YOUR_PROXY", "https": "YOUR_PROXY"},
       }
       return proxies.get(site)
   ```

   Then run with those sites; the scraper will use the proxy.

**Warning:** These sites may still return 0 jobs or errors for India. The safe‑site filter prevents them from breaking your main run.

### C. Add Your Own Site

1. Create a new package under `jobspy/` (e.g., `jobspy/mysite/`).
2. Implement:
   - `constant.py` (headers, query templates)
   - `util.py` (helpers)
   - `mysite.py` (scraper class inheriting `Scraper`)
3. Register it in `jobspy/scrape_jobs.py` under `SCRAPER_MAPPING`.
4. Test with:

   ```bash
   python main.py "Your Query" -s mysite
   ```

## 🧪 Testing Individual Modules

Run each scraper in isolation to see which work:

```bash
# LinkedIn
python -c "from jobspy.pipeline import discover_jobs; jobs = discover_jobs(keywords=['IT Support'], location='India', results_wanted=5, sites=['linkedin']); print(f'LinkedIn: {len(jobs)} jobs')"

# Naukri
python -c "from jobspy.pipeline import discover_jobs; jobs = discover_jobs(keywords=['IT Support'], location='India', results_wanted=5, sites=['naukri']); print(f'Naukri: {len(jobs)} jobs')"

# RemoteRocketship
python -c "from jobspy.pipeline import discover_jobs; jobs = discover_jobs(keywords=['IT Support'], location='India', results_wanted=5, sites=['remote_rocketship']); print(f'RemoteRocketship: {len(jobs)} jobs')"
```

## 🐛 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 0 jobs from Indeed/Google | Region‑restricted for India | Use `--remote` to force US location or skip these sites |
| 403 from ZipRecruiter/Glassdoor | Cloudflare block | Add a residential proxy or skip them |
| `AttributeError: 'Glassdoor' object has no attribute '_get_csrf_token'` | Incomplete Glassdoor scraper | Skip Glassdoor or provide a working implementation |
| Slow runs | No proxies for blocked sites | Add proxies or remove blocked sites from your list |

## 📦 Dependencies

- `requests` – HTTP client
- `beautifulsoup4` – HTML parsing
- `markdownify` – HTML → Markdown
- `pydantic` – Data validation
- `pandas` – CSV output
- `numpy` – Math helpers

## 🤝 Contributing

1. Fork the repository.
2. Add tests under `jobspy/tests/`.
3. Update the README if you add a new site or major feature.
4. Submit a pull request.

## 📄 License

MIT – see `LICENSE`.

## 🙏 Acknowledgments

- The project leverages public job‑board APIs and HTML structures. Respect the sites’ robots.txt and terms of service.
- The resume‑matching logic is tuned for Alok Garg’s profile; you can adjust keywords in `jobspy/evaluator.py`.

---

**Happy hunting! 🚀**

---

## 🧑‍💻 Developer notes (quick)

- Run a dry (no-network) pipeline for quick verification:
  ```bash
  python main.py --dry --results 2 --output outputs/dry_out.csv
  ```

- Run a short live run to validate scrapers (small results):
  ```bash
  python main.py --results 5 --output outputs/live_test.csv
  ```

- Manual tests (no pytest required):
  ```bash
  python tests/run_manual_tests.py
  ```

- Tests added: basic utils, Naukri parsing, and a dry pipeline smoke test. Use `pytest` if you install it (`pip install pytest`).

- If you want CI friendly tests, I can add GitHub Actions and ensure `pytest` runs on PRs.

