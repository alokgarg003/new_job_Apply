"""Run a quick smoke test for JobSpy.
Usage: python scripts/run_smoke_test.py
"""
from pprint import pprint
import sys
from pathlib import Path

# Ensure local package imports work when running the script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobspy import scrape_jobs

if __name__ == "__main__":
    try:
        print("Running smoke test: LinkedIn + Indeed, 3 results each, location='India'")
        df = scrape_jobs(site_name=["linkedin", "indeed"], search_term="Software Engineer", location="India", results_wanted=3, verbose=1)
        print(f"Result DataFrame shape: {df.shape}")
        pprint(df.head().to_dict(orient='records'))
    except Exception as e:
        print("Smoke test failed with exception:")
        print(e)
