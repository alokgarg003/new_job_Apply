# jobspy/evaluator.py
from __future__ import annotations
import re
from typing import List, Dict
import settings

def norm_text(text: str) -> str:
    if not text: return ""
    return text.lower()

class ProfileMatchEvaluator:
    def __init__(self):
        self.exp_regex = re.compile(r"(?P<min>\d+)[+]?\s*[-–to]{0,3}\s*(?P<max>\d+)?\s*years?", re.I)

    def _extract_skills(self, text: str) -> List[str]:
        txt = norm_text(text)
        found = set()
        for skill in settings.PROFILE_PRIMARY_SKILLS + settings.PROFILE_SECONDARY_SKILLS:
            if skill in txt:
                found.add(skill)
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
        return any(k in txt for k in ["on-call", "on call", "rota", "rotation", "shift", "night shift", "24x7"])

    def _detect_mft(self, text: str) -> bool:
        txt = norm_text(text)
        return any(k in txt for k in ["mft", "goanywhere", "go-anywhere", "go anywhere", "managed file transfer", "fms", "ftg"])

    def _detect_cloud(self, text: str) -> List[str]:
        txt = norm_text(text)
        clouds = []
        if "azure" in txt: clouds.append("Azure")
        if "aws" in txt: clouds.append("AWS")
        if "gcp" in txt or "google cloud" in txt: clouds.append("GCP")
        return clouds

    def _detect_support_signal(self, text: str) -> tuple[bool, List[str]]:
        txt = norm_text(text)
        support_keywords = ["production", "support", "incident", "l2", "l3", "troubleshoot", "root cause",
                           "incident management", "problem management", "service desk", "ticket"]
        dev_keywords = ["develop", "implementation", "design", "feature", "software engineer", "engineer -"]
        has_support = any(k in txt for k in support_keywords)
        has_dev = any(k in txt for k in dev_keywords)
        return has_support and not has_dev, [k for k in support_keywords if k in txt]

    def evaluate(self, text: str) -> Dict:
        txt = text or ""
        score = 0
        reasons: List[str] = []
        key_skills = self._extract_skills(txt)

        lowered = norm_text(txt)
        for ex in settings.PROFILE_EXCLUDE_SIGNALS:
            try:
                if re.search(rf"\b{re.escape(ex)}\b", lowered, re.I):
                    return {
                        "match_score": 0,
                        "match_reasons": [f"Exclusion signal: '{ex}'"],
                        "missing_skills": [],
                        "key_skills": key_skills,
                        "experience_range": self._extract_experience(txt),
                        "resume_alignment_level": "Ignore",
                    }
            except re.error:
                if ex in lowered:
                    return {
                        "match_score": 0,
                        "match_reasons": [f"Exclusion signal: '{ex}'"],
                        "missing_skills": [],
                        "key_skills": key_skills,
                        "experience_range": self._extract_experience(txt),
                        "resume_alignment_level": "Ignore",
                    }

        primary_hits = [s for s in key_skills if s in settings.PROFILE_PRIMARY_SKILLS]
        secondary_hits = [s for s in key_skills if s in settings.PROFILE_SECONDARY_SKILLS]

        score += min(len(primary_hits) * settings.EVAL_PRIMARY_WEIGHT, 60)
        if primary_hits: reasons.append(f"Primary skills: {', '.join(primary_hits)}")

        score += min(len(secondary_hits) * settings.EVAL_SECONDARY_WEIGHT, 15)
        if secondary_hits: reasons.append(f"Secondary skills: {', '.join(secondary_hits)}")

        if self._detect_mft(txt):
            score += settings.EVAL_MFT_BONUS
            reasons.append("MFT / file transfer tools")
        if self._detect_oncall(txt):
            score += settings.EVAL_ONCALL_BONUS
            reasons.append("On-call / shift work")
        clouds = self._detect_cloud(txt)
        if clouds:
            score += min(5 * len(clouds), 10)
            reasons.append(f"Cloud: {', '.join(clouds)}")
        if any(k in lowered for k in ["servicenow", "itil", "incident"]):
            score += 8
            reasons.append("ServiceNow/ITIL/incident")
        if any(k in lowered for k in ["jenkins", "ci/cd"]):
            score += 4
            reasons.append("CI/CD")
        support_signal, _ = self._detect_support_signal(txt)
        if support_signal:
            score += settings.EVAL_SUPPORT_BONUS
            reasons.append("Support/production oriented")
        else:
            if any(k in lowered for k in ["software engineer", "senior backend", "full stack", "frontend"]):
                reasons.append("Development heavy; down-ranked")
                score = max(score - settings.EVAL_DEV_PENALTY, 0)

        score = max(0, min(100, int(score)))
        desired = ["linux", "sftp", "servicenow", "itil"]
        missing = [d for d in desired if d not in key_skills and d not in lowered]

        if score >= 70: level = "Strong Match"
        elif score >= 45: level = "Good Match"
        elif score >= 20: level = "Stretch Role"
        else: level = "Ignore"

        exp = self._extract_experience(txt)
        if exp: reasons.append(f"Experience: {exp}")

        return {
            "match_score": score,
            "match_reasons": reasons,
            "missing_skills": missing,
            "key_skills": key_skills,
            "experience_range": exp,
            "resume_alignment_level": level,
            "why_this_job_fits": "; ".join(reasons) if reasons else None,
        }