import csv
import os
import sys
import tempfile
from datetime import datetime
import traceback

import pandas as pd
from jobspy import scrape_jobs

# Focus on the two sites that are currently working for you.
SITES = ["indeed", "linkedin"]  # change to include other sites if/when needed
SEARCH_TERM = "application support"
GOOGLE_SEARCH_TERM = "application support jobs in India since yesterday"
LOCATION = "India"
RESULTS_WANTED = 100
HOURS_OLD = 24
COUNTRY_INDEED = "India"
# PROXIES = ["user:pass@host:port", "host2:port"]
PROXIES = None

OUTPUT_FILENAME = "application_support_jobs_india.csv"

site_results = []
site_status = {}

for site in SITES:
    print(f"\n--- Scraping {site} ---")
    try:
        df = scrape_jobs(
            site_name=[site],
            search_term=SEARCH_TERM,
            google_search_term=GOOGLE_SEARCH_TERM,
            location=LOCATION,
            results_wanted=RESULTS_WANTED,
            hours_old=HOURS_OLD,
            country_indeed=COUNTRY_INDEED,
            proxies=PROXIES,
        )
        count = len(df) if hasattr(df, "__len__") else 0
        site_results.append(df)
        site_status[site] = {"status": "success", "count": count}
        print(f"{site}: success — {count} jobs")
    except Exception as e:
        site_status[site] = {"status": "error", "error": str(e)}
        print(f"{site}: error — {e}")
        traceback.print_exc()

# Combine results
if site_results:
    jobs = pd.concat(site_results, ignore_index=True)
else:
    jobs = pd.DataFrame()

print("\n=== Summary ===")
for site, info in site_status.items():
    if info["status"] == "success":
        print(f"- {site}: OK ({info['count']} jobs)")
    else:
        print(f"- {site}: ERROR ({info.get('error')})")

# Robust CSV write with fallbacks for PermissionError or other IO issues

def try_write_csv(df: pd.DataFrame, filename: str) -> str | None:
    try:
        df.to_csv(filename, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
        return filename
    except PermissionError as e:
        print(f"PermissionError: cannot write to '{filename}' — {e}")
        return None
    except Exception as e:
        print(f"Error writing CSV to '{filename}': {e}")
        return None

if jobs.empty:
    print("No jobs to write.")
    sys.exit(0)

print(f"\nAttempting to write output to '{OUTPUT_FILENAME}'")
written = try_write_csv(jobs, OUTPUT_FILENAME)
if not written:
    # Fallback 1: timestamped filename in current directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    alt_name = f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{ts}.csv"
    print(f"Trying fallback filename '{alt_name}'")
    written = try_write_csv(jobs, alt_name)

if not written:
    # Fallback 2: write to user's temp directory
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{ts}.csv")
    print(f"Trying fallback temp path '{temp_path}'")
    written = try_write_csv(jobs, temp_path)

if not written:
    # Final fallback: print first few rows to stdout and instruct user
    print("\nUnable to write CSV to disk. Showing first 10 rows instead:")
    print(jobs.head(10).to_string())
    print("\nSuggested actions:")
    print("1) Close any application (Excel, editor) that might have the file open.")
    print("2) Run the script with elevated permissions or change the output filename/path.")
    print("3) Ensure the directory is writable and you have sufficient disk space.")
    print("4) If you want, provide an alternate path (e.g., 'C:/Users/you/Documents/') and I'll try saving there.")
else:
    print(f"Wrote output to: {written}")

# Exit with non-zero code if any site failed
failed_sites = [s for s, info in site_status.items() if info["status"] != "success"]
if failed_sites:
    print(f"\nWarning: some sites failed: {failed_sites}")
    print("If you want, I can try using proxies for those sites or enable header/TLS tweaks.")
    sys.exit(2)

print("\nAll done — no site errors detected.")

