# jobspy/repositories/profile_repository.py
"""
Profile repository for user profile operations.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from .base_repository import BaseRepository


class ProfileRepository(BaseRepository):
    """Repository for profile operations."""

    def __init__(self):
        super().__init__("profiles")

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find profile by email."""
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("email", email)\
                .maybe_single()\
                .execute()
            return response.data
        except Exception as e:
            self.log.error(f"Error finding profile by email: {e}")
            return None

    def update_skills(self, profile_id: UUID, skills: list) -> bool:
        """Update profile skills."""
        try:
            self.update(profile_id, {"skills": skills})
            return True
        except Exception as e:
            self.log.error(f"Error updating skills: {e}")
            return False

    def get_preferences(self, profile_id: UUID) -> Dict[str, Any]:
        """Get user preferences."""
        profile = self.get_by_id(profile_id)
        return profile.get("preferences", {}) if profile else {}
