# jobspy/tests/03_test_debug_file_and_normalization.py
import pytest
import pandas as pd
import os
from jobspy.pipeline import normalize_output_df

def test_debug_file_and_normalization():
    df = pd.DataFrame({
        "location": ["{city: 'City', state: 'State'}"],
        "key_skills": [["skill1", "skill2"]],
        "match_reasons": [["reason1", "reason2"]],
    })
    df_norm = normalize_output_df(df)
    assert isinstance(df_norm["key_skills"].iloc[0], str)
    assert "," in df_norm["key_skills"].iloc[0]