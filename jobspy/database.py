# jobspy/database.py
"""
Database connection and session management using Supabase.
"""
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from jobspy.config import get_config
from jobspy.util import create_logger

log = create_logger("Database")


class Database:
    """Supabase database client wrapper with connection pooling."""

    _instance: Optional['Database'] = None
    _client: Optional[Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            config = get_config()
            try:
                self._client = create_client(
                    config.database.url,
                    config.database.anon_key
                )
                log.info("Database connection established")
            except Exception as e:
                log.error(f"Failed to connect to database: {e}")
                raise

    @property
    def client(self) -> Client:
        """Get the Supabase client."""
        if self._client is None:
            raise RuntimeError("Database not initialized")
        return self._client

    def table(self, name: str):
        """Get a table reference."""
        return self.client.table(name)

    def close(self):
        """Close database connection."""
        self._client = None
        log.info("Database connection closed")


# Singleton instance
db = Database()


def get_db() -> Database:
    """Dependency injection helper for database."""
    return db
