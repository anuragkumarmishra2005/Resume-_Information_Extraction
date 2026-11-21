"""Unit tests for skills extraction, taxonomy matching, and category preservation."""

from resume_parser.extractors.skills import (
    extract_skills,
    load_taxonomy,
    canonicalize_skill,
)


def test_taxonomy_loaded():
    taxonomy, categories, canonical_list = load_taxonomy()
    assert len(taxonomy) >= 300
    assert "python" in taxonomy
    assert "docker" in taxonomy
    assert "react" in taxonomy
    assert taxonomy["python"] == "Python"


def test_canonicalize_and_fuzzy_matching():
    taxonomy, _, canonical_list = load_taxonomy()
    assert canonicalize_skill("python", taxonomy, canonical_list) == "Python"
    assert canonicalize_skill("ReactJS", taxonomy, canonical_list) == "React JS" or canonicalize_skill("ReactJS", taxonomy, canonical_list) == "React"
    assert canonicalize_skill("Machine Learning (Beginner)", taxonomy, canonical_list) == "Machine Learning"


def test_categorized_skills_extraction():
    skills_text = """
    • Languages: Python, Java, SQL, Rust
    • Databases: PostgreSQL, MongoDB, Redis
    • Tools: Git, Docker, Kubernetes
    • Soft Skills: Leadership, Communication
    """
    skills_data = extract_skills(skills_text, skills_text)

    assert "Languages" in skills_data.by_category
    assert "Databases" in skills_data.by_category
    assert "Tools" in skills_data.by_category
    assert "Soft Skills" in skills_data.by_category

    assert "Python" in skills_data.by_category["Languages"]
    assert "PostgreSQL" in skills_data.by_category["Databases"]
    assert "Kubernetes" in skills_data.by_category["Tools"]
    assert "Leadership" in skills_data.by_category["Soft Skills"]

    # All skills should aggregate all of them
    assert "Python" in skills_data.all
    assert "PostgreSQL" in skills_data.all
    assert "Rust" in skills_data.all
