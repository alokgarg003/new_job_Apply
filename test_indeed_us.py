from jobspy.pipeline import discover_jobs
jobs = discover_jobs(keywords=["Application Support"], location="United States", results_wanted=5, sites=["indeed"])
print(f"Indeed US jobs: {len(jobs)}")
for j in jobs[:3]:
    print(j["title"], j["company"], j["job_url"])