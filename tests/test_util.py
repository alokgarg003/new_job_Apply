# tests/test_util.py
import pytest
from jobspy.util import get_enum_from_value, get_enum_from_job_type, extract_job_type
from jobspy.model import JobType, Country


def test_get_enum_from_value():
    assert get_enum_from_value(Country, "india") == Country.INDIA
    assert get_enum_from_value(Country, "USA") == Country.USA


def test_get_enum_from_job_type():
    assert get_enum_from_job_type("fulltime") == JobType.FULL_TIME
    assert get_enum_from_job_type("internship") == JobType.INTERNSHIP


def test_extract_job_type():
    res = extract_job_type(["fulltime", JobType.CONTRACT])
    assert JobType.FULL_TIME in res and JobType.CONTRACT in res