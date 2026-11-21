"""Main extraction pipeline orchestrating text extraction, segmentation, and field parsing."""

import logging
import time
from typing import BinaryIO, List, Optional, Union

from resume_parser.extractors.contact import extract_contact_info
from resume_parser.extractors.education import extract_education
from resume_parser.extractors.experience import extract_experience
from resume_parser.extractors.projects import extract_projects
from resume_parser.extractors.sections import segment_sections
from resume_parser.extractors.skills import extract_skills
from resume_parser.extractors.text_extractor import extract_document
from resume_parser.models import MetaData, ResumeData

logger = logging.getLogger(__name__)


def parse_achievements(achievements_text: str) -> List[str]:
    """Parse achievements and certifications section into a list of strings."""
    if not achievements_text.strip():
        return []

    lines = achievements_text.splitlines()
    achievements: List[str] = []
    current_bullet: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("•", "*", "- ", "– ", "+ ")):
            if current_bullet:
                achievements.append(current_bullet)
            clean = stripped.lstrip("•*-+– ").strip()
            current_bullet = clean
        elif current_bullet is not None:
            current_bullet += " " + stripped
        else:
            achievements.append(stripped)

    if current_bullet:
        achievements.append(current_bullet)

    return achievements


def parse_resume(
    file_input: Union[str, bytes, BinaryIO],
    filename: str = "resume.pdf",
) -> ResumeData:
    """End-to-end resume information extraction pipeline.

    Args:
        file_input: File path, raw bytes, or file-like buffer.
        filename: Name of the uploaded file.

    Returns:
        Structured ResumeData conforming to target JSON schema.
    """
    start_time = time.perf_counter()
    warnings: List[str] = []

    try:
        # 1. Document text and layout extraction
        doc = extract_document(file_input, filename)
        warnings.extend(doc.warnings)

        if not doc.text.strip():
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return ResumeData(
                meta=MetaData(
                    source_file=filename,
                    pages=doc.pages,
                    extraction_time_ms=elapsed_ms,
                    warnings=warnings,
                )
            )

        # 2. Section segmentation
        sections = segment_sections(doc.text)

        # 3. Field extractors
        personal = extract_contact_info(
            header_text=sections.header_text,
            full_text=doc.text,
            document_links=doc.links,
            top_large_text=doc.top_large_text,
        )

        summary = sections.summary_text.strip() if sections.summary_text.strip() else None

        skills = extract_skills(
            skills_text=sections.skills_text,
            full_text=doc.text,
        )

        education = extract_education(
            education_text=sections.education_text,
            full_text=doc.text,
        )

        experience, non_jobs = extract_experience(
            experience_text=sections.experience_text,
            full_text=doc.text,
        )

        projects = extract_projects(
            projects_text=sections.projects_text,
            non_job_blocks=non_jobs,
        )

        achievements = parse_achievements(sections.achievements_text)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        meta = MetaData(
            source_file=filename,
            pages=doc.pages,
            extraction_time_ms=elapsed_ms,
            warnings=warnings,
        )

        return ResumeData(
            personal=personal,
            summary=summary,
            skills=skills,
            education=education,
            experience=experience,
            projects=projects,
            achievements=achievements,
            meta=meta,
        )

    except Exception as e:
        logger.exception("Unexpected error during resume extraction: %s", e)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        warnings.append(f"Unexpected error encountered during parsing: {str(e)}")
        return ResumeData(
            meta=MetaData(
                source_file=filename,
                pages=1,
                extraction_time_ms=elapsed_ms,
                warnings=warnings,
            )
        )
