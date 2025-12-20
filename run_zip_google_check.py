from jobspy import scrape_jobs

# try ziprecruiter with US
print('ZipRecruiter (US):')
df = scrape_jobs(site_name=['ziprecruiter'], search_term='Application Support', location='United States', results_wanted=10)
print('Rows:', None if df is None else len(df))
if df is not None and not df.empty:
    print(df[['site','title','job_url']].head().to_string())

# try google with simplified query
print('\nGoogle (simplified query):')
df2 = scrape_jobs(site_name=['google'], search_term='Application Support', location='India', results_wanted=10)
print('Rows:', None if df2 is None else len(df2))
if df2 is not None and not df2.empty:
    print(df2[['site','title','job_url']].head().to_string())
