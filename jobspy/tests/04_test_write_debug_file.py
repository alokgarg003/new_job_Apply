# jobspy/tests/04_test_write_debug_file.py
import pytest
import pandas as pd
from datetime import datetime
from jobspy.pipeline import run_personalized_pipeline

def test_write_debug_file():
    # This test just confirms the function runs without raising
    # (actual file I/O in tests should be mocked in a real suite)
    output = run_personalized_pipeline(
        keywords=["test"],
        location="India",
        results_wanted=5,
        output_file="test_output.csv",
    )
    assert isinstance(output, pd.DataFrame)