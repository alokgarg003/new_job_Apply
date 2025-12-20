import re
import pandas as pd
from jobspy.pipeline import make_debug_filename, normalize_output_df


def test_debug_filename_format():
    name = make_debug_filename('alok_personalized.csv')
    assert name.endswith('.csv')
    assert '_debug_' in name
    # expect pattern like _debug_YYYYMMDD_HHMMSS.csv
    assert re.search(r'_debug_\d{8}_\d{6}\.csv$', name)


def test_normalize_output_df_location_and_lists():
    df = pd.DataFrame([
        {
            'title': 'T',
            'location': "{'country': None, 'city': 'Test City', 'state': None}",
            'key_skills': "['a', 'b']",
            'skills': ['x', 'y'],
            'missing_skills': None,
        }
    ])

    out = normalize_output_df(df)
    assert out.loc[0, 'location'] == 'Test City'
    assert out.loc[0, 'key_skills'] == 'a, b'
    assert out.loc[0, 'skills'] == 'x, y'
