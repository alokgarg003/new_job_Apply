from jobspy import scrape_jobs

sites = ['google', 'ziprecruiter', 'naukri', 'linkedin', 'indeed', 'dice', 'wellfound', 'remoteok', 'weworkremotely', 'remoterocketship']
for s in sites:
    print('\n=== Checking site:', s)
    df = scrape_jobs(site_name=[s], search_term='"Application Support" OR "Production Support"', location='India', results_wanted=10)
    if df is None or df.empty:
        print('No results from', s)
    else:
        print('Found', len(df), 'records from', s)
        print(df[['site', 'title', 'job_url']].head().to_string())
