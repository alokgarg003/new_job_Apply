# run_discover.py
"""
Quick discovery mode – prints URLs and basic job metadata without enrichment.
"""

from jobspy.pipeline import discover_jobs

if __name__ == "__main__":
    keywords = ["Application Support", "ServiceNow", "IT Support"]
    location = "India"
    results_wanted = 100
    sites = ["indeed", "linkedin", "google", "naukri"]

    jobs = discover_jobs(keywords=keywords, location=location, results_wanted=results_wanted, sites=sites)
    print(f"Discovered {len(jobs)} jobs")
    for job in jobs:
        print(f"{job['site']}: {job['title']} @ {job['company']} – {job['job_url']}")