import pandas as pd
from jobspy.pipeline import normalize_output_df


def test_normalize_location_and_lists():
    df = pd.DataFrame([
        {
            "title": "Test Role",
            "location": {"city": "Bengaluru", "state": "KA", "country": "India"},
            "key_skills": ["python", "linux"],
            "missing_skills": ["servicenow"],
        }
    ])

    out = normalize_output_df(df)
    assert "location" in out.columns
    assert out.loc[0, "location"] in ("Bengaluru, KA, India", "Bengaluru, KA, India")
    assert out.loc[0, "key_skills"] == "python, linux"
    assert out.loc[0, "missing_skills"] == "servicenow"
