LinkedIn contact extractor

Usage:

python linkedin_contact_extractor.py --input path/to/profiles.csv --output-dir outputs

Notes:
- Input CSV must have a `profile_url` column.
- Script appends `/overlay/contact-info/` and attempts to fetch public contact info.
- Some LinkedIn pages are blocked (HTTP 999) or require login and will be marked private.
- If `openpyxl` isn't installed, script will write CSV files instead of Excel and log a warning.
- Please avoid excessive runs against LinkedIn and respect their terms of service.
