High-level architecture (prototype)

Components
- Frontend (prototype): Streamlit app (`webapp/streamlit_app.py`) to upload/select inputs, start test runs, and visualize outputs.
- Backend API: FastAPI (`webapp/api.py`) to list outputs and provide preview endpoints and synchronous test run endpoint.
- Extractors: Existing scripts (refactor target `jobspy/linkedin/extractors.py`) will be exposed as callables.
- Persistence: Outputs stored in `outputs/` (CSV/Excel) and a small SQLite DB for job metadata (future).
- Workers: RQ or Celery will be added later for async processing; initial prototype uses synchronous subprocess calls for test runs.

Deployment & runtime
- Local dev: Run `streamlit run webapp/streamlit_app.py` and `uvicorn webapp.api:app --reload` for API.
- Dockerization: Provide Dockerfiles and compose in a later step for production-like setups.

Security & Operational Notes
- Credentials remain required for authenticated runs and must be provided via env vars.
- Rate-limiting, proxies, and rotation are necessary for large runs; those are part of "hardening" work later.
