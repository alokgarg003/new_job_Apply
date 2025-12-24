Project redesign plan — JobSpy UI and orchestration

Scope
- Provide a small web frontend to browse and showcase extraction outputs (personalized views, downloads).
- Provide an API to list available result files and stream previews.
- Refactor extractors into importable interfaces for later background job orchestration.
- Provide a Streamlit app for rapid prototyping and a FastAPI backend for programmatic access.

Constraints
- Keep changes incremental and backwards compatible with current `removed_scripts/` and `outputs/` layout.
- Minimal external dependencies: FastAPI + Uvicorn, Streamlit, RQ/Celery deferred to later steps, SQLite for job state.
- Respect LinkedIn terms of service; extraction remains local and requires user-provided credentials.

Acceptance criteria
- `webapp/api.py` exposes endpoints: `/health`, `/outputs` (list files), `/outputs/{name}` (preview/download), `/run` (start a run synchronously for testing).
- `webapp/streamlit_app.py` allows the user to pick an output CSV and view it as an interactive table and download it.
- A basic `docs/architecture.md` describing intended architecture, next steps (job queue, auth, Docker, CI).

Next immediate steps
1. Implement the FastAPI skeleton and a minimal Streamlit app that reads `outputs/` CSV files.
2. Refactor extractor functions into `jobspy/linkedin/extractors.py` in next iteration.
3. Add CI, Dockerization and background workers in subsequent tasks.

Notes
- This is an incremental, testable redesign — we'll implement components and add tests as we go. If you want me to proceed with background job queue and full auth-ready web UI next, I'll implement that after this prototype is validated.
