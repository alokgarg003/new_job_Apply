import sys
from pathlib import Path
# Ensure the project root is on sys.path when running this script directly
sys.path.append(str(Path(__file__).resolve().parents[1]))
from jobspy.pipeline import make_debug_filename, normalize_output_df
import pandas as pd

rows = [
    {
        'title': 'T',
        'company_name': 'C',
        'location': "{'country': None, 'city': 'Test City', 'state': None}",
        'key_skills': "['a', 'b']",
        'skills': ['x', 'y'],
        'match_score': 42,
        'match_reasons': "['reason1', 'reason2']",
    }
]

df = pd.DataFrame(rows)
df = normalize_output_df(df)
fn = make_debug_filename('test_output.csv')
df.to_csv(fn, index=False)
print('Wrote', fn)
