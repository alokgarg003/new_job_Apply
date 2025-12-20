from jobspy.pipeline import run_personalized_pipeline

kws = [
    'Application Support',
    'Production Support',
    'Technical Analyst',
    'L2 Support',
    'MFT Support',
    'Linux Support Engineer',
]
df = run_personalized_pipeline(kws, 'India', results_wanted=10, output_file='alok_personalized.csv')
print('Finished. Output rows:', getattr(df, 'shape', None))
print(df.head())
