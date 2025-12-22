# run_discover.py
from jobspy.pipeline import discover_jobs

if __name__ == "__main__":
    keywords = ["Application Support", "ServiceNow", "IT Support"]
    location = "India"
    results_wanted = 100
    sites = ["linkedin", "naukri"]

    jobs = discover_jobs(keywords=keywords, location=location, results_wanted=results_wanted, sites=sites)
    print(f"Discovered {len(jobs)} jobs")
    for job in jobs:
        print(f"{job['site']}: {job['title']} @ {job['company']} – {job['job_url']}")