"""Unit tests for section heading detection and document segmentation."""

from resume_parser.extractors.sections import (
    is_heading_candidate,
    segment_sections,
    SEC_SUMMARY,
    SEC_EDUCATION,
    SEC_SKILLS,
    SEC_EXPERIENCE,
    SEC_PROJECTS,
    SEC_ACHIEVEMENTS,
)


def test_heading_candidate_recognition():
    # Valid headings
    assert is_heading_candidate("EDUCATION") == SEC_EDUCATION
    assert is_heading_candidate("Academic Background") == SEC_EDUCATION
    assert is_heading_candidate("WORK EXPERIENCE") == SEC_EXPERIENCE
    assert is_heading_candidate("Professional Experience:") == SEC_EXPERIENCE
    assert is_heading_candidate("Technical Skills") == SEC_SKILLS
    assert is_heading_candidate("Core Competencies") == SEC_SKILLS
    assert is_heading_candidate("Projects") == SEC_PROJECTS
    assert is_heading_candidate("Certifications & Awards") == SEC_ACHIEVEMENTS
    assert is_heading_candidate("Profile") == SEC_SUMMARY

    # Non-headings (bullets, long sentences, URLs)
    assert is_heading_candidate("• Developed full stack web applications in Python") is None
    assert is_heading_candidate("- Managed a team of 5 software engineers") is None
    assert is_heading_candidate("Responsible for designing scalable microservices in AWS") is None
    assert is_heading_candidate("https://linkedin.com/in/user") is None


def test_segment_sections_flow():
    doc_text = """
    Alex Taylor
    New York, NY | alex@taylor.dev

    PROFESSIONAL SUMMARY
    Results-driven engineer with 5 years experience building cloud applications.

    EDUCATION
    Master of Science in Computer Science
    Columbia University, New York, NY
    2019 - 2021

    TECHNICAL SKILLS
    • Languages: Python, Go, TypeScript
    • Cloud: AWS, Docker, Kubernetes

    EXPERIENCE
    Senior Backend Engineer
    Stripe, New York, NY
    2021 - Present
    • Architected payments service with 99.99% uptime.

    PROJECTS
    Distributed Cache Engine
    • Built an in-memory key-value store in Go.

    ACHIEVEMENTS
    • AWS Certified Solutions Architect Professional
    """
    segmented = segment_sections(doc_text)

    assert "Alex Taylor" in segmented.header_text
    assert "Results-driven engineer" in segmented.summary_text
    assert "Master of Science in Computer Science" in segmented.education_text
    assert "Languages: Python" in segmented.skills_text
    assert "Senior Backend Engineer" in segmented.experience_text
    assert "Distributed Cache Engine" in segmented.projects_text
    assert "AWS Certified Solutions Architect" in segmented.achievements_text
