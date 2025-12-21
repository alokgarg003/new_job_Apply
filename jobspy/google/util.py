# jobspy/google/util.py
import re

# Import create_logger from the top-level util module
from jobspy.util import create_logger

log = create_logger("Google")

def find_job_info_initial_page(html_text: str):
    """Find job data in the initial HTML page."""
    pattern = r'520084652":(\[.*?\]\s*])\s*}\s*]\s*]\s*]\s*]\s*]'
    results = []
    matches = re.finditer(pattern, html_text, re.DOTALL)
    import json
    for match in matches:
        try:
            parsed_data = json.loads(match.group(1))
            results.append(parsed_data)
        except json.JSONDecodeError:
            continue
    return results

def find_job_info(jobs_data):
    """Find job listings from parsed JSON data."""
    if isinstance(jobs_data, dict):
        if "520084652" in jobs_data and isinstance(jobs_data["520084652"], list):
            return jobs_data["520084652"]
        for v in jobs_data.values():
            res = find_job_info(v)
            if res:
                return res
    elif isinstance(jobs_data, list):
        for item in jobs_data:
            res = find_job_info(item)
            if res:
                return res
    return None