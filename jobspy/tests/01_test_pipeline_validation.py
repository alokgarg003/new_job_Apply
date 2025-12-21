# jobspy/tests/01_test_pipeline_validation.py
import pytest
from jobspy.pipeline import validate_discovery_row

def test_validate_discovery_row():
    assert validate_discovery_row({}) == (False, "empty row")
    assert validate_discovery_row({"job_url": "http://x.com"}) == (True, None)
    assert validate_discovery_row({"job_url": "http://x.com", "site": "linkedin"}) == (True, None)