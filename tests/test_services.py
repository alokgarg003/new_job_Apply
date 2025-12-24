# tests/test_services.py
"""
Tests for service layer.
"""
import pytest
from uuid import uuid4
from jobspy.services import MatchingService


def test_matching_service_initialization():
    """Test matching service initialization."""
    service = MatchingService()
    assert service is not None
    assert service.config is not None


def test_match_evaluation(test_profile, sample_job_data):
    """Test job matching evaluation."""
    service = MatchingService()

    result = service._evaluate_match(test_profile, sample_job_data)

    assert "match_score" in result
    assert "alignment_level" in result
    assert "matching_skills" in result
    assert "missing_skills" in result
    assert isinstance(result["match_score"], int)
    assert 0 <= result["match_score"] <= 100


def test_skill_extraction():
    """Test skill extraction from text."""
    service = MatchingService()
    cfg = service.config.matching

    text = "Experience with Python, AWS, Linux, and Jenkins required"
    skills = service._extract_skills(text, cfg)

    assert isinstance(skills, list)
    assert "python" in skills
    assert "aws" in skills
    assert "linux" in skills


def test_experience_extraction():
    """Test experience extraction."""
    service = MatchingService()

    text1 = "5+ years of experience required"
    exp1 = service._extract_experience(text1)
    assert exp1 == "5+ years"

    text2 = "3-5 years experience"
    exp2 = service._extract_experience(text2)
    assert exp2 == "3-5 years"


def test_cloud_detection():
    """Test cloud platform detection."""
    service = MatchingService()

    text = "Experience with AWS, Azure, and GCP required"
    clouds = service._detect_cloud(text.lower())

    assert "AWS" in clouds
    assert "Azure" in clouds
    assert "GCP" in clouds


def test_exclude_signals():
    """Test exclusion signals."""
    service = MatchingService()

    job_data = {
        "title": "Frontend React Developer",
        "description": "Looking for React and Angular expert"
    }

    result = service._evaluate_match({}, job_data)
    assert result["alignment_level"] == "Ignore"
    assert "Exclusion signal" in result["match_reasons"][0]
