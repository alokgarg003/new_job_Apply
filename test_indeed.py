# test_indeed.py
from jobspy.pipeline import discover_jobs

jobs = discover_jobs(
    keywords=["Application Support"],
    location="India",
    results_wanted=5,
    sites=["indeed"]
)

print(f"Indeed jobs: {len(jobs)}")
for j in jobs[:3]:
    print(j["title"], j["company"], j["job_url"])