Providers design

Goal: Provide pluggable provider implementations that are robust and allow using paid/official APIs where available, and stealthy scraper fallback when APIs don't exist or keys are unavailable.

Providers should:
- Implement `jobspy.providers.Provider` (method `fetch_contacts(input_csv, options) -> (public_rows, private_rows)`)
- Be registered with `@register_provider` so they appear in `jobspy.providers.list_providers()`
- Normalize output rows to `profile_url, linkedin, website, phone, email, connected_since` for public rows and `profile_url, reason` for private rows

Included providers:
- `clearbit` — best-effort integration with Clearbit Person API when `CLEARBIT_KEY` is available or supplied via options. Falls back to marking rows private when key missing.
- `playwright` — stealthy browser-based fallback using Playwright; supports proxy, pool/session rotation, single-driver mode, and basic anti-detection injections. Use `proxies` (comma-separated string or list) and `pool_size` options to assign proxies to pool members and rotate them automatically when blocked.

Next steps:
- Add a Clearbit rate-limit/backoff policy and a provider orchestrator for sequential fallbacks. (Implemented: `jobspy/providers/utils.py` and `jobspy/providers/orchestrator.py`).
- Add additional providers (e.g., Hunter, Apollo) and allow provider chaining and orchestration with retry/backoff.
- Add CI integration tests that mock provider responses (basic orchestrator tests added in `tests/test_orchestrator.py`).
