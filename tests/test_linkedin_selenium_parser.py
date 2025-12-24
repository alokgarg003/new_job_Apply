from removed_scripts.linkedin_contact_extractor_selenium import parse_contact_html

SAMPLE_HTML = '''
<div class="pv-contact-info__contact-type ci-email">
  <a href="mailto:alice@example.com">Email</a>
</div>
<div class="pv-contact-info__contact-type ci-phone">
  <a href="tel:+1-555-123-4567">Phone</a>
</div>
<div class="pv-contact-info__contact-type ci-websites">
  <a href="https://example.com">Website</a>
</div>
<p>Connected since January 2020</p>
'''


def test_parse_contact_html_basic():
    parsed = parse_contact_html(SAMPLE_HTML)
    assert parsed["email"] == "alice@example.com"
    assert "+1-555-123-4567" in parsed["phone"]
    assert parsed["website"] == "https://example.com"
    assert "January" in parsed["connected_since"]
