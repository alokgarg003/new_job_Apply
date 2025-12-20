from jobspy.pipeline import discover_jobs, enrich_job

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
for i, meta in enumerate(rows[:10]):
    print(f"\n[{i+1}] Enriching: {meta.get('job_url')} - {meta.get('title')} @ {meta.get('company')} ({meta.get('location')})")
    print('   meta site:', meta.get('site'), 'meta is_remote:', meta.get('is_remote'), 'meta wfh:', meta.get('work_from_home_type'))
    post = enrich_job(meta)
    if post:
        print('-> score:', post.match_score, 'level:', post.resume_alignment_level)
        print('-> reasons:', post.match_reasons)
        print('-> is_remote:', post.is_remote, 'work_from_home_type:', post.work_from_home_type, 'site:', post.site)
    else:
        print('-> enrichment failed or returned None')
