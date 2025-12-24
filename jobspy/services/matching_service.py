# jobspy/services/matching_service.py
"""
Enhanced matching service with improved scoring algorithm.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
from jobspy.repositories import JobMatchRepository, ProfileRepository, JobRepository
from jobspy.config import get_config
from jobspy.util import create_logger, norm_text

log = create_logger("MatchingService")


class MatchingService:
    """Service for matching jobs to user profiles with intelligent scoring."""

    def __init__(self):
        self.match_repo = JobMatchRepository()
        self.profile_repo = ProfileRepository()
        self.job_repo = JobRepository()
        self.config = get_config()
        self.exp_regex = re.compile(
            r"(?P<min>\d+)[+]?\s*[-–to]{0,3}\s*(?P<max>\d+)?\s*years?",
            re.I
        )

    def match_jobs_for_search(
        self,
        profile_id: UUID,
        search_id: UUID,
        job_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Match jobs from a search to a profile.

        Args:
            profile_id: User profile ID
            search_id: Search ID
            job_ids: Specific job IDs to match (if None, matches all from search)

        Returns:
            Dict with match statistics and top matches
        """
        profile = self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        if job_ids:
            jobs = [self.job_repo.get_by_id(jid) for jid in job_ids]
            jobs = [j for j in jobs if j]
        else:
            jobs = self.job_repo.find_all(limit=1000)

        matches = []
        strong_matches = 0
        good_matches = 0
        stretch_matches = 0

        for job in jobs:
            if not job:
                continue

            match_result = self._evaluate_match(profile, job)

            if match_result["alignment_level"] == "Ignore":
                continue

            match_data = {
                "profile_id": str(profile_id),
                "job_id": job["id"],
                "search_id": str(search_id),
                "match_score": match_result["match_score"],
                "alignment_level": match_result["alignment_level"],
                "matching_skills": match_result["matching_skills"],
                "missing_skills": match_result["missing_skills"],
                "match_reasons": match_result["match_reasons"],
                "why_fits": match_result["why_fits"]
            }

            matches.append(match_data)

            if match_result["alignment_level"] == "Strong Match":
                strong_matches += 1
            elif match_result["alignment_level"] == "Good Match":
                good_matches += 1
            elif match_result["alignment_level"] == "Stretch Role":
                stretch_matches += 1

        if matches:
            self.match_repo.bulk_create_matches(matches)

        top_matches = sorted(
            matches,
            key=lambda x: x["match_score"],
            reverse=True
        )[:20]

        return {
            "total_matches": len(matches),
            "strong_matches": strong_matches,
            "good_matches": good_matches,
            "stretch_matches": stretch_matches,
            "top_matches": top_matches
        }

    def _evaluate_match(
        self,
        profile: Dict[str, Any],
        job: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate how well a job matches a profile.

        Returns match details with score and reasoning.
        """
        cfg = self.config.matching

        text = f"{job.get('title', '')} {job.get('description', '')}"
        lowered = norm_text(text)

        for exclude_signal in cfg.exclude_signals:
            try:
                if re.search(rf"\b{re.escape(exclude_signal)}\b", lowered, re.I):
                    return self._create_ignore_match(
                        f"Exclusion signal: '{exclude_signal}'"
                    )
            except re.error:
                if exclude_signal in lowered:
                    return self._create_ignore_match(
                        f"Exclusion signal: '{exclude_signal}'"
                    )

        score = 0
        reasons = []
        key_skills = self._extract_skills(text, cfg)

        profile_skills = profile.get("skills", [])
        if isinstance(profile_skills, str):
            profile_skills = [s.strip() for s in profile_skills.split(",")]

        primary_hits = [
            s for s in key_skills
            if s in cfg.primary_skills or s in profile_skills
        ]
        secondary_hits = [
            s for s in key_skills
            if s in cfg.secondary_skills
        ]

        score += min(len(primary_hits) * cfg.primary_weight, 60)
        if primary_hits:
            reasons.append(f"Primary skills: {', '.join(primary_hits[:5])}")

        score += min(len(secondary_hits) * cfg.secondary_weight, 15)
        if secondary_hits:
            reasons.append(f"Secondary skills: {', '.join(secondary_hits[:3])}")

        if self._detect_mft(lowered):
            score += cfg.mft_bonus
            reasons.append("MFT / file transfer tools")

        if self._detect_oncall(lowered):
            score += cfg.oncall_bonus
            reasons.append("On-call / shift work")

        clouds = self._detect_cloud(lowered)
        if clouds:
            score += min(5 * len(clouds), 10)
            reasons.append(f"Cloud: {', '.join(clouds)}")

        if any(k in lowered for k in ["servicenow", "itil", "incident"]):
            score += 8
            reasons.append("ServiceNow/ITIL/incident")

        if any(k in lowered for k in ["jenkins", "ci/cd", "cicd"]):
            score += 4
            reasons.append("CI/CD")

        if self._is_support_oriented(lowered):
            score += cfg.support_bonus
            reasons.append("Support/production oriented")
        elif self._is_dev_heavy(lowered):
            reasons.append("Development heavy; down-ranked")
            score = max(score - cfg.dev_penalty, 0)

        exp_match = self._extract_experience(text)
        if exp_match:
            reasons.append(f"Experience: {exp_match}")
            profile_exp = profile.get("experience_years", 0)
            if self._check_experience_match(exp_match, profile_exp):
                score += 5
                reasons.append("Experience level matches")

        score = max(0, min(100, int(score)))

        if score >= 70:
            level = "Strong Match"
        elif score >= 45:
            level = "Good Match"
        elif score >= 20:
            level = "Stretch Role"
        else:
            level = "Ignore"

        desired_skills = ["linux", "sftp", "servicenow", "itil"]
        missing = [d for d in desired_skills if d not in key_skills and d not in lowered]

        return {
            "match_score": score,
            "alignment_level": level,
            "matching_skills": primary_hits + secondary_hits,
            "missing_skills": missing,
            "match_reasons": reasons,
            "why_fits": "; ".join(reasons) if reasons else ""
        }

    def _create_ignore_match(self, reason: str) -> Dict[str, Any]:
        """Create an ignore match result."""
        return {
            "match_score": 0,
            "alignment_level": "Ignore",
            "matching_skills": [],
            "missing_skills": [],
            "match_reasons": [reason],
            "why_fits": reason
        }

    def _extract_skills(self, text: str, cfg) -> List[str]:
        """Extract skills from text."""
        txt = norm_text(text)
        found = set()

        for skill in cfg.primary_skills + cfg.secondary_skills:
            skill_pattern = skill.replace("_", "[ _-]?")
            if re.search(rf"\b{re.escape(skill_pattern)}\b", txt, re.I):
                found.add(skill)

        if any(k in txt for k in ["service now", "service-now", "servicenow"]):
            found.add("servicenow")

        return sorted(found)

    def _extract_experience(self, text: str) -> Optional[str]:
        """Extract experience requirement."""
        m = self.exp_regex.search(text)
        if m:
            min_exp = m.group("min")
            max_exp = m.group("max")
            if max_exp:
                return f"{min_exp}-{max_exp} years"
            return f"{min_exp}+ years"
        return None

    def _check_experience_match(self, req: str, profile_exp: int) -> bool:
        """Check if profile experience matches requirement."""
        if not req or profile_exp == 0:
            return False

        match = re.search(r"(\d+)(?:-(\d+))?\+?\s*years?", req, re.I)
        if not match:
            return False

        min_req = int(match.group(1))
        max_req = int(match.group(2)) if match.group(2) else min_req + 5

        return min_req <= profile_exp <= max_req

    def _detect_mft(self, text: str) -> bool:
        """Detect MFT/file transfer tools."""
        keywords = [
            "mft", "goanywhere", "go-anywhere", "go anywhere",
            "managed file transfer", "fms", "ftg"
        ]
        return any(k in text for k in keywords)

    def _detect_oncall(self, text: str) -> bool:
        """Detect on-call requirements."""
        keywords = [
            "on-call", "on call", "rota", "rotation",
            "shift", "night shift", "24x7", "24/7"
        ]
        return any(k in text for k in keywords)

    def _detect_cloud(self, text: str) -> List[str]:
        """Detect cloud platforms."""
        clouds = []
        if "azure" in text:
            clouds.append("Azure")
        if "aws" in text:
            clouds.append("AWS")
        if "gcp" in text or "google cloud" in text:
            clouds.append("GCP")
        return clouds

    def _is_support_oriented(self, text: str) -> bool:
        """Check if job is support-oriented."""
        support_keywords = [
            "production", "support", "incident", "l2", "l3",
            "troubleshoot", "root cause", "incident management",
            "problem management", "service desk", "ticket"
        ]
        return sum(1 for k in support_keywords if k in text) >= 2

    def _is_dev_heavy(self, text: str) -> bool:
        """Check if job is development-heavy."""
        dev_keywords = [
            "develop", "implementation", "design", "feature",
            "software engineer", "engineer -", "architect"
        ]
        return sum(1 for k in dev_keywords if k in text) >= 2

    def get_top_matches(
        self,
        profile_id: UUID,
        min_score: int = 45,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get top matches for a profile."""
        return self.match_repo.get_top_matches(
            profile_id=profile_id,
            min_score=min_score,
            limit=limit
        )
