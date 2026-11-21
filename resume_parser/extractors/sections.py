"""Section segmentation for resume documents.

Identifies major sections (Header/Contact, Summary, Education, Skills,
Experience, Projects, Achievements) using heading patterns, typography,
and layout cues.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard section identifiers
SEC_HEADER = "HEADER"
SEC_SUMMARY = "SUMMARY"
SEC_EDUCATION = "EDUCATION"
SEC_SKILLS = "SKILLS"
SEC_EXPERIENCE = "EXPERIENCE"
SEC_PROJECTS = "PROJECTS"
SEC_ACHIEVEMENTS = "ACHIEVEMENTS"

# Heading regex patterns (case-insensitive)
SECTION_HEADING_PATTERNS: List[Tuple[str, re.Pattern]] = [
    (
        SEC_SUMMARY,
        re.compile(
            r"^(?:profile|professional\s+summary|summary\s+of\s+qualifications|career\s+profile|professional\s+profile|about\s+me|career\s+objective|summary|executive\s+summary)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
    (
        SEC_EDUCATION,
        re.compile(
            r"^(?:education\s+and\s+qualifications|educational\s+background|academic\s+background|academic\s+qualifications|educational\s+qualifications|education\s+&\s+qualifications|academics|education)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
    (
        SEC_SKILLS,
        re.compile(
            r"^(?:technical\s+skills|technical\s+proficiencies|core\s+competencies|skills\s+&\s+technologies|skills\s+and\s+tools|skills\s+&\s+tools|key\s+skills|skills\s+summary|technologies|areas\s+of\s+expertise|skills)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
    (
        SEC_PROJECTS,
        re.compile(
            r"^(?:key\s+projects|featured\s+projects|notable\s+projects|selected\s+projects|software\s+projects|technical\s+projects|academic\s+and\s+personal\s+projects|projects)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
    (
        SEC_EXPERIENCE,
        re.compile(
            r"^(?:work\s+experience|professional\s+experience|employment\s+history|work\s+history|career\s+history|relevant\s+experience|internship\s+experience|experience)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
    (
        SEC_ACHIEVEMENTS,
        re.compile(
            r"^(?:certifications\s+&\s+awards|certifications\s+and\s+awards|achievements\s+&\s+awards|achievements\s+and\s+awards|awards\s+&\s+achievements|awards\s+and\s+achievements|honors\s+&\s+awards|honours\s+&\s+awards|awards|certifications|certificates|licenses\s+&\s+certifications|achievements|accomplishments|publications|extracurricular\s+activities|leadership\s+activities|volunteering)[\s:\-—]*$",
            re.IGNORECASE,
        ),
    ),
]


def is_heading_candidate(line: str) -> Optional[str]:
    """Determine if a line is a section heading.

    Args:
        line: Stripped line text.

    Returns:
        Section key string (e.g. 'EXPERIENCE') or None.
    """
    cleaned = line.strip()
    if not cleaned:
        return None

    # Lines starting with bullet points or dashes are not headings
    if cleaned.startswith(("•", "*", "- ", ">", "+", "–")):
        return None

    # Heading lines are short (usually 1-5 words, < 60 chars)
    if len(cleaned) > 60 or len(cleaned.split()) > 6:
        return None

    # Strip surrounding decorators like --- Education --- or ### Education
    trimmed = re.sub(r"^[\s#\-_=~*|]+|[\s#\-_=~*|]+$", "", cleaned).strip()
    if not trimmed:
        return None

    for section_type, pattern in SECTION_HEADING_PATTERNS:
        if pattern.match(trimmed):
            return section_type

    return None


@dataclass
class SegmentedDocument:
    """Document segmented into logical sections."""
    header_text: str = ""
    summary_text: str = ""
    education_text: str = ""
    skills_text: str = ""
    experience_text: str = ""
    projects_text: str = ""
    achievements_text: str = ""
    raw_sections: Dict[str, List[str]] = field(default_factory=dict)


def segment_sections(full_text: str) -> SegmentedDocument:
    """Segment a resume's clean text into structured sections.

    Args:
        full_text: Normalized full resume text.

    Returns:
        SegmentedDocument with per-section content.
    """
    lines = full_text.splitlines()
    sections: Dict[str, List[str]] = {
        SEC_HEADER: [],
        SEC_SUMMARY: [],
        SEC_EDUCATION: [],
        SEC_SKILLS: [],
        SEC_EXPERIENCE: [],
        SEC_PROJECTS: [],
        SEC_ACHIEVEMENTS: [],
    }

    current_section = SEC_HEADER

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section in sections:
                sections[current_section].append("")
            continue

        detected_section = is_heading_candidate(stripped)
        if detected_section is not None:
            current_section = detected_section
            logger.debug("Switched section to %s on line: '%s'", current_section, stripped)
            continue

        sections[current_section].append(line)

    # Clean up trailing/leading blank lines for each section
    def join_clean(lines_list: List[str]) -> str:
        return "\n".join(lines_list).strip()

    return SegmentedDocument(
        header_text=join_clean(sections[SEC_HEADER]),
        summary_text=join_clean(sections[SEC_SUMMARY]),
        education_text=join_clean(sections[SEC_EDUCATION]),
        skills_text=join_clean(sections[SEC_SKILLS]),
        experience_text=join_clean(sections[SEC_EXPERIENCE]),
        projects_text=join_clean(sections[SEC_PROJECTS]),
        achievements_text=join_clean(sections[SEC_ACHIEVEMENTS]),
        raw_sections=sections,
    )
