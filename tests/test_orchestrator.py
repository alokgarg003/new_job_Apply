from jobspy.providers.orchestrator import ProviderOrchestrator
from jobspy.providers import list_providers


def test_orchestrator_happy_path(tmp_path):
    # create a small CSV used by providers (Clearbit will return no-key private markers)
    p = tmp_path / "input.csv"
    p.write_text("URL\nhttps://www.linkedin.com/in/example\n")
    orch = ProviderOrchestrator(['clearbit', 'playwright'], retry_attempts=1, base_delay=0.1)
    # run with options that will cause clearbit to record private and playwright may not be available in CI
    public, private = orch.run(str(p), options={'url_column': 'URL'})
    assert isinstance(public, list)
    assert isinstance(private, list)
