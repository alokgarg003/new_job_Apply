# jobspy/repositories/base_repository.py
"""
Base repository with common CRUD operations.
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from uuid import UUID
from jobspy.database import get_db
from jobspy.util import create_logger

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository providing common database operations."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db = get_db()
        self.log = create_logger(f"Repo:{table_name}")

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new record."""
        try:
            response = self.db.table(self.table_name).insert(data).execute()
            if response.data:
                self.log.debug(f"Created record in {self.table_name}")
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as e:
            self.log.error(f"Error creating record: {e}")
            raise

    def get_by_id(self, record_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a record by ID."""
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("id", str(record_id))\
                .maybe_single()\
                .execute()
            return response.data
        except Exception as e:
            self.log.error(f"Error fetching record {record_id}: {e}")
            return None

    def update(self, record_id: UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record."""
        try:
            response = self.db.table(self.table_name)\
                .update(data)\
                .eq("id", str(record_id))\
                .execute()
            if response.data:
                self.log.debug(f"Updated record {record_id}")
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as e:
            self.log.error(f"Error updating record {record_id}: {e}")
            raise

    def delete(self, record_id: UUID) -> bool:
        """Delete a record."""
        try:
            self.db.table(self.table_name)\
                .delete()\
                .eq("id", str(record_id))\
                .execute()
            self.log.debug(f"Deleted record {record_id}")
            return True
        except Exception as e:
            self.log.error(f"Error deleting record {record_id}: {e}")
            return False

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Find all records with pagination."""
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .range(offset, offset + limit - 1)\
                .execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error fetching records: {e}")
            return []

    def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Find records matching filters."""
        try:
            query = self.db.table(self.table_name).select("*")
            for key, value in filters.items():
                query = query.eq(key, value)
            response = query.limit(limit).execute()
            return response.data or []
        except Exception as e:
            self.log.error(f"Error finding records: {e}")
            return []

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        try:
            query = self.db.table(self.table_name).select("id", count="exact")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            response = query.execute()
            return response.count or 0
        except Exception as e:
            self.log.error(f"Error counting records: {e}")
            return 0
