#!/usr/bin/env python3
import sys
import os
# Ensure repo root is on path so we can import local package in this runner
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from jobspy.util import get_enum_from_value, get_enum_from_job_type, extract_job_type
from jobspy.model import Country, JobType
from jobspy.naukri.util import parse_job_type, parse_company_industry
import settings
from jobspy.pipeline import run_personalized_pipeline

errors = []
# test_get_enum_from_value
try:
    assert get_enum_from_value(Country, 'india') == Country.INDIA
    assert get_enum_from_value(Country, 'USA') == Country.USA
    print('test_get_enum_from_value: OK')
except Exception as e:
    errors.append(('test_get_enum_from_value', str(e)))

# test_get_enum_from_job_type
try:
    assert get_enum_from_job_type('fulltime') == JobType.FULL_TIME
    assert get_enum_from_job_type('internship') == JobType.INTERNSHIP
    print('test_get_enum_from_job_type: OK')
except Exception as e:
    errors.append(('test_get_enum_from_job_type', str(e)))

# test_extract_job_type
try:
    res = extract_job_type(['fulltime', JobType.CONTRACT])
    assert JobType.FULL_TIME in res and JobType.CONTRACT in res
    print('test_extract_job_type: OK')
except Exception as e:
    errors.append(('test_extract_job_type', str(e)))

# test_parse_job_type_from_html
try:
    html = '<span class="job-type">Fulltime</span>'
    res = parse_job_type(html)
    assert res and res[0].name == 'FULL_TIME'
    print('test_parse_job_type_from_html: OK')
except Exception as e:
    errors.append(('test_parse_job_type_from_html', str(e)))

# test_parse_company_industry_from_html
try:
    html = '<span class="industry">Information Technology</span>'
    res = parse_company_industry(html)
    assert res == 'Information Technology'
    print('test_parse_company_industry_from_html: OK')
except Exception as e:
    errors.append(('test_parse_company_industry_from_html', str(e)))

# test_pipeline_dry_mode
try:
    settings.DRY_RUN = True
    df = run_personalized_pipeline(['test'], None, 1, output_file=None)
    print('test_pipeline_dry_mode: OK (returned rows=%d)' % (0 if df is None else len(df)))
    settings.DRY_RUN = False
except Exception as e:
    errors.append(('test_pipeline_dry_mode', str(e)))

if errors:
    print('\nERRORS:')
    for name, msg in errors:
        print(name, msg)
    sys.exit(1)
else:
    print('\nAll manual tests passed')