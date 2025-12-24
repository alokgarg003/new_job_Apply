# jobspy/services/profile_service.py
"""
Profile service for managing user profiles and preferences.
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from jobspy.repositories import ProfileRepository
from jobspy.util import create_logger

log = create_logger("ProfileService")


class ProfileService:
    """Service for profile operations."""

    def __init__(self):
        self.profile_repo = ProfileRepository()

    def create_profile(
        self,
        profile_id: UUID,
        email: str,
        full_name: Optional[str] = None,
        resume_text: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_years: int = 0,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new user profile."""
        data = {
            "id": str(profile_id),
            "email": email,
            "full_name": full_name,
            "resume_text": resume_text,
            "skills": skills or [],
            "experience_years": experience_years,
            "preferences": preferences or {}
        }

        profile = self.profile_repo.create(data)
        if not profile:
            raise Exception("Failed to create profile")

        log.info(f"Profile created: {profile_id}")
        return profile

    def get_profile(self, profile_id: UUID) -> Optional[Dict[str, Any]]:
        """Get profile by ID."""
        return self.profile_repo.get_by_id(profile_id)

    def get_profile_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get profile by email."""
        return self.profile_repo.find_by_email(email)

    def update_profile(
        self,
        profile_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update profile data."""
        return self.profile_repo.update(profile_id, updates)

    def update_skills(self, profile_id: UUID, skills: List[str]) -> bool:
        """Update profile skills."""
        return self.profile_repo.update_skills(profile_id, skills)

    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Parse resume text to extract skills and experience.
        This is a simple keyword-based approach. In production,
        you'd use NLP or an AI service.
        """
        skills = []
        common_skills = [
            "python", "java", "javascript", "react", "angular",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "sql", "mongodb", "postgresql", "linux", "git"
        ]

        lower_text = resume_text.lower()
        for skill in common_skills:
            if skill in lower_text:
                skills.append(skill)

        exp_match = None
        import re
        exp_pattern = r"(\d+)\+?\s*years?\s+(?:of\s+)?experience"
        match = re.search(exp_pattern, lower_text, re.I)
        if match:
            exp_match = int(match.group(1))

        return {
            "skills": skills,
            "experience_years": exp_match or 0,
            "resume_text": resume_text
        }

    def update_preferences(
        self,
        profile_id: UUID,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences."""
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        current_prefs = profile.get("preferences", {})
        current_prefs.update(preferences)

        self.update_profile(profile_id, {"preferences": current_prefs})
        return True
