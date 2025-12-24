from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any


class Provider(ABC):
    """Abstract provider interface. Implementations should return (public_rows, private_rows)."""

    name: str

    @abstractmethod
    def fetch_contacts(self, input_csv: str, options: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """Run provider for the given input CSV.

        Returns:
            public_rows: list of dicts with normalized fields (profile_url, linkedin, website, phone, email, connected_since)
            private_rows: list of dicts with (profile_url, reason)
        """
        raise NotImplementedError


_PROVIDERS = {}


def register_provider(cls):
    _PROVIDERS[cls.name] = cls
    return cls


def get_provider(name: str):
    cls = _PROVIDERS.get(name)
    if not cls:
        raise KeyError(f"Provider not found: {name}")
    return cls()


def list_providers():
    return list(_PROVIDERS.keys())
