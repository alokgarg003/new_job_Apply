from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import pandas as pd
from typing import List

app = FastAPI(title="JobSpy API")

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs'))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/outputs", response_model=List[str])
def list_outputs():
    files = []
    try:
        for f in sorted(os.listdir(OUTPUT_DIR)):
            if f.lower().endswith('.csv') or f.lower().endswith('.xlsx'):
                files.append(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not list outputs")
    return files


@app.get("/providers")
def list_providers_api():
    from jobspy.providers import list_providers

    return list_providers()


@app.post("/run-provider")
def run_provider(provider: str, input_csv: str = 'removed_scripts/test_connections_100.csv', options: Dict = None):
    """Run a provider synchronously (for small test workloads)."""
    from jobspy.providers import get_provider
    if options is None:
        options = {}
    try:
        prov = get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    try:
        public_rows, private_rows = prov.fetch_contacts(input_csv, options)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # persist checkpoint
    import pandas as pd
    import os as _os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pub_path = _os.path.join(OUTPUT_DIR, f"public_{provider}_{ts}.csv")
    priv_path = _os.path.join(OUTPUT_DIR, f"private_{provider}_{ts}.csv")
    pd.DataFrame(public_rows).to_csv(pub_path, index=False)
    pd.DataFrame(private_rows).to_csv(priv_path, index=False)
    return {"public_path": pub_path, "private_path": priv_path, "public_count": len(public_rows), "private_count": len(private_rows)}


@app.post("/run-orchestrator")
def run_orchestrator(providers: str = 'playwright,clearbit', input_csv: str = 'removed_scripts/test_connections_100.csv', options: Dict = None):
    """Run a chain of providers with fallback and backoff."""
    from jobspy.providers.orchestrator import ProviderOrchestrator
    if options is None:
        options = {}
    provider_list = [p.strip() for p in providers.split(',') if p.strip()]
    orch = ProviderOrchestrator(provider_list, retry_attempts=3, base_delay=0.5)
    try:
        public_rows, private_rows = orch.run(input_csv, options)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # persist checkpoint
    import pandas as pd
    import os as _os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pub_path = _os.path.join(OUTPUT_DIR, f"public_orch_{ts}.csv")
    priv_path = _os.path.join(OUTPUT_DIR, f"private_orch_{ts}.csv")
    pd.DataFrame(public_rows).to_csv(pub_path, index=False)
    pd.DataFrame(private_rows).to_csv(priv_path, index=False)
    return {"public_path": pub_path, "private_path": priv_path, "public_count": len(public_rows), "private_count": len(private_rows), "providers": provider_list}

@app.get("/outputs/{name}/preview")
def preview_output(name: str, rows: int = 20):
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        if name.lower().endswith('.csv'):
            df = pd.read_csv(path, nrows=rows)
        else:
            df = pd.read_excel(path, nrows=rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return df.to_dict(orient='records')

@app.get("/outputs/{name}/download")
def download_output(name: str):
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type='application/octet-stream', filename=name)

@app.post("/run-test")
def run_test(profile_csv: str = 'removed_scripts/test_connections_100.csv', single_driver: bool = True):
    """Synchronous test-run using selenium extractor. Use for small samples only."""
    from subprocess import Popen, PIPE
    import shlex
    if not os.path.exists(profile_csv):
        raise HTTPException(status_code=400, detail=f"Input CSV not found: {profile_csv}")
    cmd = f"python removed_scripts/linkedin_contact_extractor_selenium.py --input {shlex.quote(profile_csv)} --url-column URL --output-dir outputs --batch-size 10 --workers 1"
    if single_driver:
        cmd += " --single-driver"
    p = Popen(cmd, shell=True)
    return {"started": True, "pid": p.pid, "cmd": cmd}
