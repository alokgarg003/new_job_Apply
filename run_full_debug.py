from jobspy.pipeline import discover_jobs, enrich_job, make_debug_filename
from jobspy.model import Location
import pandas as pd

kws = [
    'Application Support',
    'Production Support',
    'Technical Analyst',
    'L2 Support',
    'MFT Support',
    'Linux Support Engineer',
]
rows = discover_jobs(kws, location='India', results_wanted=10)
print('Discovered:', len(rows))
posts = []
for i, meta in enumerate(rows[:10]):
    print(f"\n[{i+1}] Enriching: {meta.get('job_url')} - {meta.get('title')} @ {meta.get('company')} ({meta.get('location')})")
    post = enrich_job(meta)
    if post:
        print('-> score:', post.match_score, 'level:', post.resume_alignment_level)
        posts.append(post.dict())
    else:
        print('-> enrichment failed or returned None')

if posts:
    df = pd.DataFrame(posts)

    # Normalize location and list fields for readability
    if 'location' in df.columns:
        def _normalize_location(val):
            try:
                if isinstance(val, dict):
                    return Location(**val).display_location()
                if isinstance(val, str) and val.strip().startswith('{'):
                    import ast
                    try:
                        d = ast.literal_eval(val)
                        if isinstance(d, dict):
                            return Location(**d).display_location()
                    except Exception:
                        return val
                return val
            except Exception:
                return str(val)
        df['location'] = df['location'].apply(_normalize_location)

    for list_col in ('key_skills', 'missing_skills', 'match_reasons'):
        if list_col in df.columns:
            df[list_col] = df[list_col].apply(lambda v: ', '.join(v) if isinstance(v, list) else v)

    debug_name = make_debug_filename('alok_personalized.csv')
    df.to_csv(debug_name, index=False)
    print('\nWrote', debug_name, 'with', len(df), 'rows')
else:
    print('\nNo posts to write')
