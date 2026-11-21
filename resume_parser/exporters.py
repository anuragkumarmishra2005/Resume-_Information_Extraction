"""Exporters for converting structured ResumeData into JSON and CSV tabular formats."""

import io
import json
from typing import List, Optional, Tuple, Union
import pandas as pd

from resume_parser.models import ResumeData


def export_to_json(data: ResumeData, indent: int = 2) -> str:
    """Export ResumeData to indented JSON string matching the target schema."""
    return data.to_json(indent=indent)


def export_candidate_to_flattened_dict(data: ResumeData) -> dict:
    """Flatten a ResumeData object into a single-row dictionary for CSV export."""
    p = data.personal
    links = p.links

    # Flatten skills categories
    cat_strs = [f"{cat}: {', '.join(skills)}" for cat, skills in data.skills.by_category.items()]
    skills_cat_joined = "; ".join(cat_strs)

    # Flatten education
    edu_strs = []
    for e in data.education:
        parts = [p for p in [e.degree, e.institution, e.location] if p]
        dates = f"({e.start_year or ''} - {e.end_year or ''})".strip(" -()")
        summary = " | ".join(parts)
        if dates:
            summary += f" ({dates})"
        edu_strs.append(summary)

    # Flatten experience
    exp_strs = []
    for exp in data.experience:
        parts = [p for p in [exp.title, exp.organization, exp.location] if p]
        dates = f"{exp.start_date or ''} - {exp.end_date or ''}".strip(" -")
        exp_summary = " | ".join(parts)
        if dates:
            exp_summary += f" [{dates}]"
        exp_strs.append(exp_summary)

    # Flatten projects
    proj_strs = []
    for proj in data.projects:
        p_name = proj.name or "Untitled Project"
        techs = f"Techs: {', '.join(proj.technologies)}" if proj.technologies else ""
        proj_summary = f"{p_name} ({techs})" if techs else p_name
        proj_strs.append(proj_summary)

    return {
        "name": p.name or "",
        "emails": "; ".join(p.emails),
        "phones": "; ".join(p.phones),
        "location": p.location or "",
        "linkedin": links.linkedin or "",
        "github": links.github or "",
        "other_links": "; ".join(links.other),
        "summary": data.summary or "",
        "skills_all": "; ".join(data.skills.all),
        "skills_by_category": skills_cat_joined,
        "education": "; ".join(edu_strs),
        "experience": "; ".join(exp_strs),
        "projects": "; ".join(proj_strs),
        "achievements": "; ".join(data.achievements),
        "source_file": data.meta.source_file,
        "pages": data.meta.pages,
        "extraction_time_ms": data.meta.extraction_time_ms,
        "warnings": "; ".join(data.meta.warnings),
    }


def export_candidates_to_csv(candidates: Union[ResumeData, List[ResumeData]]) -> str:
    """Generate flattened single-row-per-candidate CSV string."""
    if isinstance(candidates, ResumeData):
        candidates = [candidates]

    rows = [export_candidate_to_flattened_dict(c) for c in candidates]
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_relational_csvs(data: ResumeData) -> Tuple[str, str, str]:
    """Generate detailed CSV strings for education, experience, and projects.

    Returns:
        Tuple of (education_csv, experience_csv, projects_csv).
    """
    # Education
    edu_rows = [
        {
            "degree": e.degree or "",
            "institution": e.institution or "",
            "location": e.location or "",
            "start_year": e.start_year or "",
            "end_year": e.end_year or "",
        }
        for e in data.education
    ]
    edu_df = pd.DataFrame(edu_rows)

    # Experience
    exp_rows = [
        {
            "title": exp.title or "",
            "organization": exp.organization or "",
            "start_date": exp.start_date or "",
            "end_date": exp.end_date or "",
            "location": exp.location or "",
            "description": "; ".join(exp.description),
        }
        for exp in data.experience
    ]
    exp_df = pd.DataFrame(exp_rows)

    # Projects
    proj_rows = [
        {
            "name": p.name or "",
            "technologies": "; ".join(p.technologies),
            "description": "; ".join(p.description),
        }
        for p in data.projects
    ]
    proj_df = pd.DataFrame(proj_rows)

    return (
        edu_df.to_csv(index=False),
        exp_df.to_csv(index=False),
        proj_df.to_csv(index=False),
    )
