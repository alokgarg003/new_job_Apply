from typing import List, Dict, Tuple, Any
from . import get_provider, list_providers
from .utils import retry_with_backoff
import logging

logger = logging.getLogger("jobspy.providers.orchestrator")


class ProviderOrchestrator:
    """Orchestrates multiple providers, applying rate-limit/backoff and fallbacks.

    Usage:
        orch = ProviderOrchestrator(['clearbit', 'playwright'])
        public, private = orch.run('input.csv', options={})
    """

    def __init__(self, providers: List[str], retry_attempts: int = 3, base_delay: float = 0.5):
        self.providers = providers
        self.retry_attempts = retry_attempts
        self.base_delay = base_delay

    def run(self, input_csv: str, options: Dict[str, Any] = None) -> Tuple[List[Dict], List[Dict]]:
        if options is None:
            options = {}
        public_acc: List[Dict] = []
        private_acc: Dict[str, Dict] = {}  # map profile_url -> reason

        # For each provider in order, try to fetch and add results. If provider fails, use retry_with_backoff
        for prov_name in self.providers:
            try:
                prov = get_provider(prov_name)
            except KeyError:
                logger.warning("Provider not found: %s", prov_name)
                continue

            logger.info("Running provider: %s", prov_name)
            def call():
                return prov.fetch_contacts(input_csv, options)

            try:
                public_rows, private_rows = retry_with_backoff(call, attempts=self.retry_attempts, base_delay=self.base_delay)
            except Exception as exc:
                logger.exception("Provider %s failed after retries: %s", prov_name, exc)
                # mark all profiles as private for this provider with the failure reason (but continue to next provider)
                import pandas as pd
                df = pd.read_csv(input_csv)
                url_col = options.get("url_column", "URL" if "URL" in df.columns else "profile_url")
                for u in df[url_col].dropna().tolist():
                    private_acc.setdefault(str(u).strip(), {"profile_url": str(u).strip(), "reason": f"provider_{prov_name}_failed"})
                continue

            # Merge public_rows - prefer first provider that returns data for a profile
            seen = set([r.get("profile_url") for r in public_acc])
            for r in public_rows:
                pu = r.get("profile_url")
                if pu not in seen:
                    public_acc.append(r)
                    seen.add(pu)
                    # if previously marked private, remove it
                    private_acc.pop(pu, None)

            # Merge private markers (only annotate if we don't have public data)
            for r in private_rows:
                pu = r.get("profile_url")
                if pu not in seen:
                    private_acc.setdefault(pu, r)

        # final lists
        public_list = public_acc
        private_list = list(private_acc.values())
        return public_list, private_list
