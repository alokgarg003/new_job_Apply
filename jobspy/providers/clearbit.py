import os
import requests
from typing import Tuple, List, Dict, Any
from ..providers import Provider, register_provider


@register_provider
class ClearbitProvider(Provider):
    name = "clearbit"

    def fetch_contacts(self, input_csv: str, options: Dict[str, Any] = None) -> Tuple[List[Dict], List[Dict]]:
        """Attempt to enrich using Clearbit Person API when possible.

        Note: Clearbit typically expects an email or domain. If no key or results, the provider
        will return private_rows noting the reason.
        """
        import pandas as pd
        if options is None:
            options = {}
        key = options.get("api_key") or os.environ.get("CLEARBIT_KEY")
        df = pd.read_csv(input_csv)
        url_col = options.get("url_column", "URL" if "URL" in df.columns else "profile_url")
        public_rows = []
        private_rows = []
        if not key:
            for u in df[url_col].dropna().tolist():
                private_rows.append({"profile_url": str(u).strip(), "reason": "clearbit_no_api_key"})
            return public_rows, private_rows

        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {key}", "User-Agent": "JobSpy-Client/1.0"})

        for u in df[url_col].dropna().tolist():
            profile_url = str(u).strip()
            # best-effort: try to call Person API using linkedin lookup param (best-effort)
            try:
                resp = session.get("https://person.clearbit.com/v2/people/find?linkedin=" + requests.utils.requote_uri(profile_url), timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    out = {
                        "profile_url": profile_url,
                        "linkedin": profile_url,
                        "website": data.get("site", {}).get("url") if isinstance(data.get("site"), dict) else None,
                        "phone": data.get("phone"),
                        "email": data.get("email"),
                        "connected_since": None,
                    }
                    public_rows.append(out)
                elif resp.status_code == 404:
                    private_rows.append({"profile_url": profile_url, "reason": "clearbit_not_found"})
                else:
                    private_rows.append({"profile_url": profile_url, "reason": f"clearbit_error_{resp.status_code}"})
            except Exception as exc:
                private_rows.append({"profile_url": profile_url, "reason": f"clearbit_exception_{str(exc)[:120]}"})
        return public_rows, private_rows
