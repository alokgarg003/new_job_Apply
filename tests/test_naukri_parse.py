# tests/test_naukri_parse.py
from jobspy.naukri.util import parse_job_type, parse_company_industry


def test_parse_job_type_from_html():
    html = '<span class="job-type">Fulltime</span>'
    res = parse_job_type(html)
    assert res and res[0].name == 'FULL_TIME'


def test_parse_company_industry_from_html():
    html = '<span class="industry">Information Technology</span>'
    res = parse_company_industry(html)
    assert res == 'Information Technology'