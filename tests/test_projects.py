"""Unit tests for projects extractor (project name, tech stack separation, wrapped bullets)."""

from resume_parser.extractors.projects import extract_projects, split_project_header


def test_split_project_header_variants():
    # Inline technologies on same line
    name, techs = split_project_header("Chat App React JS, TypeScript, Tailwind CSS")
    assert "Chat App" in name
    assert "React JS" in techs or "React" in techs
    assert "TypeScript" in techs

    # Pipe separated
    name, techs = split_project_header("E-Commerce Portal | Django, PostgreSQL, Redis")
    assert name == "E-Commerce Portal"
    assert "Django" in techs
    assert "PostgreSQL" in techs
    assert "Redis" in techs

    # Parenthesized
    name, techs = split_project_header("Mobile Health Tracker (Flutter, Firebase)")
    assert name == "Mobile Health Tracker"
    assert "Flutter" in techs
    assert "Firebase" in techs or "Firestore" in techs or "Firebase Realtime Database" in techs


def test_extract_projects_full():
    proj_text = """
    AI Document Search Engine
    Python, FastAPI, Elasticsearch, Docker
    • Built a semantic search engine indexing 50,000 PDF documents with hybrid search.
    • Deployed API containerized with Docker on AWS ECS.

    Crypto Trading Dashboard React, Vite, Tailwind CSS
    • Created real-time market data visualization using WebSocket streams.
    • Integrated authentication with JWT.
    """
    projects = extract_projects(proj_text)
    assert len(projects) == 2

    assert "AI Document Search Engine" in projects[0].name
    assert "Python" in projects[0].technologies
    assert "Elasticsearch" in projects[0].technologies
    assert len(projects[0].description) == 2

    assert "Crypto Trading Dashboard" in projects[1].name
    assert "React" in projects[1].technologies
    assert len(projects[1].description) == 2
