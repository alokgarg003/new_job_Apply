import pytest
from removed_scripts.linkedin_contact_extractor import parse_contact_info

SAMPLE_HTML = '''
<div>
  <a href="mailto:alice@example.com">Email</a>
  <a href="tel:+1-555-123-4567">Phone</a>
  <a href="https://example.com">Website</a>
  <p>Connected since January 2020</p>
</div>
'''


def test_parse_contact_info_basic():
    parsed = parse_contact_info(SAMPLE_HTML)
    assert parsed["email"] == "alice@example.com"
    assert "+1-555-123-4567" in parsed["phone"]
    assert parsed["website"] == "https://example.com"
    assert "January" in parsed["connected_since"]
