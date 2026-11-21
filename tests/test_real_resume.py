"""Automated regression test verifying tricky extraction nuances on the real resume sample."""

import os
import pytest
from resume_parser.pipeline import parse_resume

REAL_RESUME_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "sample_resumes", "AnuragMishra_resume_2026.pdf"
)


@pytest.fixture(scope="module")
def real_resume_data():
    assert os.path.exists(REAL_RESUME_PATH), f"Real resume not found at {REAL_RESUME_PATH}"
    return parse_resume(REAL_RESUME_PATH, "AnuragMishra_resume_2026.pdf")


def test_personal_info(real_resume_data):
    """Verify name, phone, email, and location are accurately captured."""
    personal = real_resume_data.personal
    assert personal.name == "Anurag Kumar Mishra"
    assert "+91 7827349893" in personal.phones
    assert "anuragkumarmishra414@gmail.com" in personal.emails
    assert personal.location == "New Delhi, India"


def test_header_links(real_resume_data):
    """Verify all four links land in links, not in the name or location."""
    links = real_resume_data.personal.links
    assert links.github is not None and "github.com" in links.github
    assert links.linkedin is not None and "linkedin.com" in links.linkedin

    all_other_str = " ".join(links.other)
    assert "leetcode.com" in all_other_str
    assert "geeksforgeeks.org" in all_other_str

    # Ensure none leaked into name or location
    assert "github.com" not in (real_resume_data.personal.name or "")
    assert "linkedin.com" not in (real_resume_data.personal.name or "")
    assert "leetcode.com" not in (real_resume_data.personal.location or "")


def test_skills_categories(real_resume_data):
    """Verify all 5 explicit skill categories are preserved in by_category."""
    by_cat = real_resume_data.skills.by_category
    assert "Languages" in by_cat
    assert "Frameworks & Libraries" in by_cat
    assert "Tools & Platforms" in by_cat
    assert "Concepts" in by_cat
    assert "Soft Skills" in by_cat

    # Check key skills within categories
    assert "Python" in by_cat["Languages"]
    assert "Flask" in by_cat["Frameworks & Libraries"]
    assert "Git" in by_cat["Tools & Platforms"]
    assert "Problem Solving" in by_cat["Soft Skills"]


def test_education_dates_null(real_resume_data):
    """Verify degree and institution are extracted, and dates are null, not guessed."""
    assert len(real_resume_data.education) >= 1
    edu = real_resume_data.education[0]
    assert "Bachelor of Computer Applications" in (edu.degree or "")
    assert "KR Mangalam University" in (edu.institution or "")
    assert edu.start_year is None, "start_year must be null when not present"
    assert edu.end_year is None, "end_year must be null when not present"


def test_experience_multi_line_and_non_job(real_resume_data):
    """Verify experience entry has title, dates, location, and org on following line,

    and that Personal & Academic Projects is not misread as a job.
    """
    exp = real_resume_data.experience
    assert len(exp) == 1, "There should be exactly 1 work experience job, not projects"

    job = exp[0]
    assert job.title == "Robotics Engineering Intern"
    assert job.organization == "Rotors"
    assert job.start_date == "June 2025"
    assert job.end_date == "July 2025"
    assert job.location == "India, Delhi"
    assert len(job.description) == 3


def test_project_heading_tech_split(real_resume_data):
    """Verify project title and technology stack are separated cleanly."""
    projects = real_resume_data.projects
    assert len(projects) >= 3

    # Check Chat Buddy AI
    chat_proj = next((p for p in projects if "Chat Buddy AI" in (p.name or "")), None)
    assert chat_proj is not None
    assert "React JS" in chat_proj.technologies or "React" in chat_proj.technologies
    assert "TypeScript" in chat_proj.technologies
    assert "Tailwind CSS" in chat_proj.technologies
    assert len(chat_proj.description) == 4

    # Check Student Performance
    student_proj = next((p for p in projects if "Student Performance" in (p.name or "")), None)
    assert student_proj is not None
    assert "Python" in student_proj.technologies
    assert "Streamlit" in student_proj.technologies
