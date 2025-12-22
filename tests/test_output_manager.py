# tests/test_output_manager.py
import pandas as pd
from pathlib import Path
from jobspy.output_manager import append_to_master


def test_append_and_dedupe(tmp_path):
    master = tmp_path / "master.csv"
    out1 = tmp_path / "out1.csv"
    out2 = tmp_path / "out2.csv"

    df1 = pd.DataFrame([
        {"id": "1", "job_url": "http://a", "title": "A", "date_posted": "2025-01-01"},
        {"id": "2", "job_url": "http://b", "title": "B", "date_posted": "2025-01-02"},
    ])
    df1.to_csv(out1, index=False)

    df2 = pd.DataFrame([
        {"id": "2", "job_url": "http://b", "title": "B-updated", "date_posted": "2025-02-02"},
        {"id": "3", "job_url": "http://c", "title": "C", "date_posted": "2025-02-01"},
    ])
    df2.to_csv(out2, index=False)

    res1 = append_to_master(out1, master)
    assert res1["added"] == 2
    res2 = append_to_master(out2, master)
    # id=2 should replace previous because of later date
    dfm = pd.read_csv(master)
    assert len(dfm) == 3
    assert (dfm[dfm.job_url == "http://b"].title.values[0]) == "B-updated"