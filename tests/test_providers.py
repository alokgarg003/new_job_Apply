from jobspy.providers import list_providers, get_provider
import pytest


def test_providers_registered():
    providers = list_providers()
    assert 'playwright' in providers
    assert 'clearbit' in providers


def test_clearbit_no_key(tmp_path):
    # create a small input csv
    p = tmp_path / "input.csv"
    p.write_text("URL\nhttps://www.linkedin.com/in/example\n")
    prov = get_provider('clearbit')
    public, private = prov.fetch_contacts(str(p), options={})
    assert isinstance(public, list)
    assert isinstance(private, list)
    assert private and private[0]['reason'].startswith('clearbit_no_api_key')
