# manual_google_debug.py

import sys
import os
from urllib.parse import urlencode

# Enable imports from jobspy module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "jobspy"))

from jobspy.google.google import Google
from jobspy.model import ScraperInput, Site

# We simulate this part of Google's internal query construction here
def build_debug_payload(session, search_term, location):
    base_url = "https://www.google.com/search"
    params = {"q": search_term, "udm": 8}
    url = f"{base_url}?{urlencode(params)}"
    print("[🔍] Simulating query URL:", url.replace(" ", "%20"))
    resp = session.get(url, timeout=15)
    print("[✅] Response size:", len(resp.text), "bytes")
    return resp.text


if __name__ == "__main__":
    keyword = "IT Support"
    locations_to_try = ["India", "Bangalore", "Mumbai", "Remote", "United States"]
    synonym_queries = [
        f'"{keyword}"',             # match quoting
        f'"{keyword}" OR "Helpdesk"',
        f'"{keyword}" OR "L2 Support"',
        f'"{keyword}" job',
        f'"{keyword}" engineer',
        f'"{keyword}" "support role"',
        f'"{keyword}" remote',
        f'"{keyword}" work from home',
        keyword,                    # unquoted variation
    ]

    print("[*] Initializing Manual Google Job Query Discovery...")
    print(f"    Testing keywords: {synonym_queries[:5]}")
    print(f"    Trying locations: {locations_to_try}")

    # Warm connection to bypass blocking where possible
    scraper = Google()
    session = scraper.session

    results = []
    seen_urls = set()

    for term in synonym_queries:
        for loc in locations_to_try:
            query = f"{term}" + (f" near {loc}" if loc else "")
            try:
                html_content = build_debug_payload(session, query, loc)

                jobs = scraper._extract_jobs_from_html(html_content)

                for job in jobs:
                    if not job.job_url:
                        continue
                    if job.job_url in seen_urls:
                        continue
                    seen_urls.add(job.job_url)
                    results.append({
                        "Query": query,
                        "Title": job.title,
                        "Company": job.company_name,
                        "URL": job.job_url,
                        "Location": job.location.display_location(),
                        "Posted": job.date_posted,
                    })

                print(f"[+] 📌 Extracted {len(jobs)} raw results for: {query}")
            except Exception as e:
                print(f"[!] 🔥 Exception on query '{query}': {type(e).__name__} — {str(e)}")
                pass

            if len(results) >= 20:  # limit to avoid excessive delay
                break
        if len(results) >= 20:
            break

    print("\n\n🎯 Final Matching Jobs Summary:")
    for r in results:
        print("-" * 80)
        print(f"[{r['Posted']}] {r['Title']} @ {r['Company']}")
        print(f"URL: {r['URL']}")
        print(f"Query Match: {r['Query']}")

    print("\n[*] Done — Total unique parsed jobs:", len(results))