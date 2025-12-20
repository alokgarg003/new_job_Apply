import os
from jobspy.pipeline import make_debug_filename, normalize_output_df
import pandas as pd


def test_write_debug_file_contains_expected_headers(tmp_path):
    rows = [
        {
            'title': 'T',
            'company_name': 'C',
            'location': "{'country': None, 'city': 'Test City', 'state': None}",
            'key_skills': "['a', 'b']",
        }
    ]
    df = pd.DataFrame(rows)
    df = normalize_output_df(df)
    outname = make_debug_filename(str(tmp_path / 'test_output.csv'))
    df.to_csv(outname, index=False)
    assert os.path.exists(outname)
    with open(outname, 'r', encoding='utf-8') as fh:
        header = fh.readline()
    # ensure expected columns are present in the header
    assert 'location' in header
    assert 'key_skills' in header
