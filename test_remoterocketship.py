# test_remoterocketship.py
from jobspy.pipeline import discover_jobs

jobs = discover_jobs(
    keywords=["Application Support"],
    location="India",
    results_wanted=5,
    sites=["remote_rocketship"]
)

print(f"RemoteRocketship jobs: {len(jobs)}")
for j in jobs[:3]:
    print(j["title"], j["company"], j["job_url"])