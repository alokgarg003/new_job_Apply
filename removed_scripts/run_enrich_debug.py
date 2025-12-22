# run_enrich_debug.py
from jobspy.pipeline import discover_jobs, validate_discovery_row, enrich_job

if __name__ == "__main__":
    keywords = ["Application Support", "ServiceNow", "IT Support"]
    location = "India"
    results_wanted = 50

    discovery = discover_jobs(keywords=keywords, location=location, results_wanted=results_wanted)
    enriched = []
    for meta in discovery:
        valid, reason = validate_discovery_row(meta)
        if not valid:
            print(f"Skipping: {reason} – {meta}")
            continue
        post = enrich_job(meta)
        if post:
            enriched.append(post)
            print(f"{post.site}: {post.title} @ {post.company_name}")
            print(f"  Match: {post.match_score} – {post.resume_alignment_level}")
            print(f"  Skills: {', '.join(post.key_skills or [])}")
            print(f"  Missing: {', '.join(post.missing_skills or [])}")
            print(f"  URL: {post.job_url}")
            print()