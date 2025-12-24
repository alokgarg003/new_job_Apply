Webapp quickstart (prototype)

1) Install additional requirements (recommended in a venv):
   pip install -r requirements_additional.txt

2) Start API:
   uvicorn webapp.api:app --reload --port 8000

3) Start Streamlit UI:
   streamlit run webapp/streamlit_app.py

Notes:
- The Streamlit app expects the API to be available at http://localhost:8000 for the quick-run button.
- For the Playwright provider, install and run browser binaries:
    playwright install
- The API's `/outputs` endpoints read files from the `outputs/` folder in the repo root.
- To use Clearbit provider, set `CLEARBIT_KEY` environment variable or provide API key in the UI.
