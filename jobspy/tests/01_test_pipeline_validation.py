from jobspy.pipeline import validate_discovery_row


def test_validate_discovery_row_accepts_good():
    meta = {
        "job_url": "https://example.com/job/1",
        "site": "linkedin",
        "title": "Eng",
        "company": "Org",
    }
    ok, reason = validate_discovery_row(meta)
    assert ok and reason is None


def test_validate_discovery_row_rejects_missing():
    meta = {"title": "no url"}
    ok, reason = validate_discovery_row(meta)
    assert not ok and reason == "missing job_url"
