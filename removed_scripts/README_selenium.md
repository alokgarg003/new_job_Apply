LinkedIn Selenium contact extractor

Overview
- Authenticated extraction of LinkedIn contact overlays using Selenium.
- Save checkpointed batch CSVs and final timestamped Excel outputs (CSV fallback).

Setup
1) Install Python deps:
   pip install selenium webdriver-manager pandas beautifulsoup4 openpyxl

2) Set credentials in environment variables:
   export LINKEDIN_USER=you@example.com
   export LINKEDIN_PASS=your_password
   (Windows: setx LINKEDIN_USER "you@example.com" etc.)

3) Run the script:
   python removed_scripts/linkedin_contact_extractor_selenium.py --input Connections1.csv --url-column URL --output-dir outputs --batch-size 200 --workers 4 --headless

Notes
- The script logs into LinkedIn and reuses authenticated cookies across worker drivers.
- Respect LinkedIn's terms; running many automated logged-in requests may violate their TOS.
- For large runs consider rotating proxies and rate-limiting.
