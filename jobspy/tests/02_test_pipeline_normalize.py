# jobspy/tests/02_test_pipeline_normalize.py
import pytest
import pandas as pd
from jobspy.pipeline import normalize_output_df

def test_normalize_output_df():
    df = pd.DataFrame({"location": ["{city: 'City', state: 'State'}"]})
    df_norm = normalize_output_df(df)
    assert "City, State" in df_norm["location"].iloc[0]