from jobspy.pipeline import discover_jobs

kws = [
    'Application Support',
    'Production Support',
    'Technical Analyst',
    'L2 Support',
    'MFT Support',
    'Linux Support Engineer',
]
rows = discover_jobs(kws, location='India', results_wanted=20)
print('Discovered rows:', len(rows))
for r in rows[:10]:
    print(r)
