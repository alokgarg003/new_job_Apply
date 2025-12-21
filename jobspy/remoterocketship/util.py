# jobspy/remoterocketship/util.py
import re
from typing import List, Dict

from jobspy.util import create_logger

log = create_logger("RemoteRocketship")

def extract_remote_info(job_json: Dict) -> Dict:
    """Extract remote‑specific fields from the job JSON."""
    return {
        "work_from_home_type": "Remote",  # RemoteRocketship is inherently remote
        "remote_details": job_json.get("remote", {}),
        "location": job_json.get("location", {}),
    }