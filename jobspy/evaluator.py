from __future__ import annotations

import re
from typing import List, Dict, Tuple

# Profile priorities for Alok Garg
PRIMARY_SKILLS = [
    "linux",
    "shell",
    "bash",
    "serviceNow".lower(),
    "servicenow",
    "itil",
    "incident",
    "sla",
    "mft",
    "sftp",
    "ftps",
    "ftp",
    "as2",
    "goanywhere",
    "fms",
    "ftg",
    "monitor",
    "monitoring",
    "alert",
    "log",
    "log analysis",
    "python",
    "jenkins",
    "bitbucket",
    "azure",
    "aws",
]

SECONDARY_SKILLS = ["java", "spring", "rest", "api", "devops", "observability", "grafana", "prometheus"]

# Role exclusion signals (strongly negative)
EXCLUDE_SIGNALS = [
    "frontend",
    "react",
    "vue",
    "angular",
    "ux",
    "ui",
    "ds(a)",
    "competitive programming",
]


def norm_text(text: str) -> str:
    if not text:
        return ""
    return text.lower()


class ProfileMatchEvaluator:
    """Evaluate a job description text against Alok Garg's profile.

    Returns a dict with match_score (0-100), match_reasons (list[str]), missing_skills (list[str]),
    key_skills_extracted (list[str]) and resume_alignment_level (one of: Strong Match, Good Match, Stretch Role, Ignore)
    """

    def __init__(self):
        # prepare compiled regex for experience
        self.exp_regex = re.compile(r"(?P<min>\d+)[+]?\s*[-–to]{0,3}\s*(?P<max>\d+)?\s*years?", re.I)

    def _extract_skills(self, text: str) -> List[str]:
        txt = norm_text(text)
        found = set()
        for skill in PRIMARY_SKILLS + SECONDARY_SKILLS:
            if skill in txt:
                found.add(skill)
        # normalize common variants
        if "service now" in txt or "service-now" in txt or "servicenow" in txt:
            found.add("servicenow")
        return sorted(found)

    def _extract_experience(self, text: str) -> str | None:
        txt = norm_text(text)
        m = self.exp_regex.search(txt)
        if m:
            min_exp = m.group("min")
            max_exp = m.group("max")
            if max_exp:
                return f"{min_exp}-{max_exp} years"
            return f"{min_exp}+ years"
        return None

    def _detect_oncall(self, text: str) -> bool:
        txt = norm_text(text)
        keywords = ["on-call", "on call", "rota", "rotation", "shift", "night shift", "24x7"]
        return any(k in txt for k in keywords)

    def _detect_mft(self, text: str) -> bool:
        txt = norm_text(text)
        mft_keys = ["mft", "goanywhere", "go-anywhere", "go anywhere", "managed file transfer", "fms", "ftg", "mft"]
        return any(k in txt for k in mft_keys)

    def _detect_cloud(self, text: str) -> List[str]:
        txt = norm_text(text)
        clouds = []
        if "azure" in txt:
            clouds.append("Azure")
        if "aws" in txt:
            clouds.append("AWS")
        if "gcp" in txt or "google cloud" in txt:
            clouds.append("GCP")
        return clouds

    def _detect_support_signal(self, text: str) -> Tuple[bool, List[str]]:
        txt = norm_text(text)
        positives = []
        support_keywords = ["production", "support", "incident", "l2", "l3", "troubleshoot", "root cause", "incident management", "problem management", "service desk", "ticket"]
        dev_keywords = ["develop", "implementation", "design", "feature", "software engineer", "engineer -" ]
        has_support = any(k in txt for k in support_keywords)
        has_dev = any(k in txt for k in dev_keywords)
        return has_support and not has_dev, [k for k in support_keywords if k in txt]

    def evaluate(self, text: str) -> Dict:
        txt = text or ""
        score = 0
        reasons: List[str] = []
        key_skills: List[str] = self._extract_skills(txt)

        # Deduct if exclusion signals found (use word-boundary matching to avoid false positives)
        lowered = norm_text(txt)
        for ex in EXCLUDE_SIGNALS:
            try:
                if re.search(rf"\b{re.escape(ex)}\b", lowered, re.I):
                    reasons.append(f"Exclusion signal detected: '{ex}'")
                    return {
                        "match_score": 0,
                        "match_reasons": reasons,
                        "missing_skills": [],
                        "key_skills": key_skills,
                        "experience_range": self._extract_experience(txt),
                        "resume_alignment_level": "Ignore",
                    }
            except re.error:
                # Fallback to substring if the pattern is invalid for some reason
                if ex in lowered:
                    reasons.append(f"Exclusion signal detected: '{ex}'")
                    return {
                        "match_score": 0,
                        "match_reasons": reasons,
                        "missing_skills": [],
                        "key_skills": key_skills,
                        "experience_range": self._extract_experience(txt),
                        "resume_alignment_level": "Ignore",
                    }

        # Primary skill hits
        primary_hits = [s for s in key_skills if s in PRIMARY_SKILLS]
        secondary_hits = [s for s in key_skills if s in SECONDARY_SKILLS]

        score += min(len(primary_hits) * 12, 60)  # up to 60 points for primary skill coverage
        if primary_hits:
            reasons.append(f"Matches primary skills: {', '.join(primary_hits)}")

        score += min(len(secondary_hits) * 5, 15)  # up to 15 for secondary
        if secondary_hits:
            reasons.append(f"Matches secondary skills: {', '.join(secondary_hits)}")

        # MFT & file transfer give bonus
        if self._detect_mft(txt):
            score += 10
            reasons.append("Mentions MFT / file transfer tools")

        # On-call / production support
        if self._detect_oncall(txt):
            score += 7
            reasons.append("On-call / shift work indicated")

        # Cloud presence
        clouds = self._detect_cloud(txt)
        if clouds:
            score += min(5 * len(clouds), 10)
            reasons.append(f"Cloud mentions: {', '.join(clouds)}")

        # ServiceNow / ITIL / incident
        if "servicenow" in key_skills or "itil" in key_skills or "incident" in lowered:
            score += 8
            reasons.append("ServiceNow/ITIL/incident handling evidence")

        # Jenkins/CI/CD
        if "jenkins" in key_skills or "ci/cd" in lowered:
            score += 4
            reasons.append("CI/CD exposure (Jenkins/Bitbucket)")

        # Support signal
        support_signal, support_evidence = self._detect_support_signal(txt)
        if support_signal:
            score += 6
            reasons.append("Role appears support/production oriented")
        else:
            # if it's strongly development oriented, down-rank
            if any(k in lowered for k in ["software engineer", "senior backend", "full stack", "frontend"]):
                reasons.append("Role appears development-heavy; down-ranked")
                score = max(score - 30, 0)

        # Final normalization
        score = max(0, min(100, int(score)))

        # Missing important skills
        desired = ["linux", "sftp", "servicenow", "itil"]
        missing = [d for d in desired if d not in key_skills and d not in lowered]

        # Levels
        if score >= 70:
            level = "Strong Match"
        elif score >= 45:
            level = "Good Match"
        elif score >= 20:
            level = "Stretch Role"
        else:
            level = "Ignore"

        # Additional small checks
        exp = self._extract_experience(txt)
        if exp:
            reasons.append(f"Experience range detected: {exp}")

        return {
            "match_score": score,
            "match_reasons": reasons,
            "missing_skills": missing,
            "key_skills": key_skills,
            "experience_range": exp,
            "resume_alignment_level": level,
        }
