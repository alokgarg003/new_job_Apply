import streamlit as st
import os
import pandas as pd
from datetime import datetime

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs'))

st.set_page_config(page_title="JobSpy Dashboard", layout="wide")
st.title("JobSpy — Extraction Results")

st.sidebar.markdown("## Actions")
if st.sidebar.button("Refresh file list"):
    st.experimental_rerun()

files = []
try:
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.lower().endswith('.csv') or f.lower().endswith('.xlsx'):
            files.append(f)
except Exception as exc:
    st.error(f"Could not list outputs: {exc}")

selected = st.sidebar.selectbox("Pick an output file", options=[''] + files)

if selected:
    st.markdown(f"### {selected}")
    path = os.path.join(OUTPUT_DIR, selected)
    try:
        if selected.lower().endswith('.csv'):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        st.dataframe(df.head(200))
        st.download_button("Download CSV", data=df.to_csv(index=False).encode('utf-8'), file_name=selected.replace('.xlsx', '.csv'))
    except Exception as exc:
        st.error(f"Failed to read file: {exc}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick test run")
profile_csv = st.sidebar.text_input("Input CSV (local path)", value='removed_scripts/test_connections_100.csv')
provider = st.sidebar.selectbox("Provider", options=['playwright', 'clearbit'])
api_key = st.sidebar.text_input("Provider API key (optional)")
provider_chain = st.sidebar.multiselect("Provider chain (order applied)", options=['playwright', 'clearbit'], default=['playwright','clearbit'])
proxy_list = st.sidebar.text_area("Proxies (comma-separated)")
pool_size = st.sidebar.number_input("Playwright pool size", min_value=1, max_value=8, value=1)
if st.sidebar.button("Start quick provider run"):
    with st.spinner("Starting provider run (synchronous, small sample)..."):
        import requests
        try:
            opts = {"api_key": api_key}
            if proxy_list:
                opts['proxies'] = proxy_list
            opts['pool_size'] = int(pool_size)
            payload = {"input_csv": profile_csv, "options": opts}
            # run orchestrator by default
            chain = ','.join(provider_chain)
            resp = requests.post(f'http://localhost:8000/run-orchestrator?providers={chain}', json=payload)
            st.success("Started: " + str(resp.json()))
        except Exception as exc:
            st.error(f"Could not start provider run: {exc}")

st.sidebar.markdown("\n\nMade with ❤️ by JobSpy prototype")
