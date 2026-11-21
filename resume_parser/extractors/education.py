"""Education background extractor.

Extracts degree, institution, location, start year, and end year.
Guarantees missing dates remain null without guessing.
"""

import logging
import re
from typing import List, Optional, Tuple
from resume_parser.models import EducationItem

logger = logging.getLogger(__name__)

DEGREE_PATTERNS = [
    re.compile(r"\b(?:Bachelor\s+of\s+[A-Za-z\s]+(?:\([A-Za-z\s]+\))?)\b", re.IGNORECASE),
    re.compile(r"\b(?:Master\s+of\s+[A-Za-z\s]+(?:\([A-Za-z\s]+\))?)\b", re.IGNORECASE),
    re.compile(r"\b(?:Doctor\s+of\s+[A-Za-z\s]+|Ph\.?D\.?)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:B\.?C\.?A\.?|M\.?C\.?A\.?|B\.?Tech\.?|M\.?Tech\.?|B\.?E\.?|M\.?E\.?|B\.?S\.?|M\.?S\.?|B\.?Sc\.?|M\.?Sc\.?|B\.?A\.?|M\.?A\.?|M\.?B\.?A\.?|B\.?B\.?A\.?|Associate\s+Degree|High\s+School|Secondary\s+School)\b",
        re.IGNORECASE,
    ),
]

INSTITUTION_KEYWORDS = [
    "university",
    "college",
    "institute",
    "school",
    "academy",
    "polytechnic",
    "campus",
    "faculty",
]

YEAR_RANGE_REGEX = re.compile(
    r"\b((?:19|20)\d{2})\s*[-–—to\s]+\s*((?:19|20)\d{2}|Present|Current|Now)\b",
    re.IGNORECASE,
)
SINGLE_YEAR_REGEX = re.compile(r"\b((?:19|20)\d{2})\b")


def parse_education_dates(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract start_year and end_year if present; otherwise return (None, None)."""
    # Check range first
    range_match = YEAR_RANGE_REGEX.search(text)
    if range_match:
        start_y = range_match.group(1).strip()
        end_y = range_match.group(2).strip()
        return start_y, end_y

    # Single year e.g. "Graduation: 2023" or "Class of 2022"
    years = SINGLE_YEAR_REGEX.findall(text)
    if len(years) == 1:
        return None, years[0]
    elif len(years) >= 2:
        return years[0], years[1]

    return None, None


def split_institution_and_location(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Split a line containing both institution and location."""
    # Look for institution keyword
    cleaned = line.strip().strip("•-*|")
    lower = cleaned.lower()

    # If pipes or bullets or commas separate institution and location
    if "|" in cleaned:
        parts = [p.strip() for p in cleaned.split("|") if p.strip()]
        inst, loc = None, None
        for p in parts:
            if any(k in p.lower() for k in INSTITUTION_KEYWORDS):
                inst = p
            elif not inst:
                inst = p
            else:
                loc = p
        return inst, loc

    # Try splitting on comma after institution keyword
    for kw in INSTITUTION_KEYWORDS:
        idx = lower.find(kw)
        if idx != -1:
            end_kw = idx + len(kw)
            comma_idx = cleaned.find(",", end_kw)
            if comma_idx != -1:
                inst = cleaned[:comma_idx].strip()
                loc = cleaned[comma_idx + 1 :].strip()
                return inst, loc
            else:
                return cleaned, None

    return cleaned, None


def extract_education(education_text: str, full_text: str = "") -> List[EducationItem]:
    """Extract structured education entries from the Education section.

    Guarantees missing fields remain None.
    """
    if not education_text.strip():
        return []

    lines = [line.strip() for line in education_text.splitlines() if line.strip()]
    items: List[EducationItem] = []

    # Cluster lines into entries. An entry typically starts with a degree or an institution
    current_entry_lines: List[str] = []

    for line in lines:
        # Check if line indicates start of new degree
        has_degree = any(pat.search(line) for pat in DEGREE_PATTERNS)
        has_inst = any(k in line.lower() for k in INSTITUTION_KEYWORDS)

        # If current entry already has lines and this line looks like a new degree
        if current_entry_lines and has_degree:
            items.append(_parse_entry_lines(current_entry_lines))
            current_entry_lines = [line]
        else:
            current_entry_lines.append(line)

    if current_entry_lines:
        items.append(_parse_entry_lines(current_entry_lines))

    return [item for item in items if item.degree or item.institution]


def _parse_entry_lines(entry_lines: List[str]) -> EducationItem:
    """Parse a cluster of lines representing a single educational background."""
    degree: Optional[str] = None
    institution: Optional[str] = None
    location: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None

    combined_text = " ".join(entry_lines)
    start_year, end_year = parse_education_dates(combined_text)

    for line in entry_lines:
        clean = line.strip().strip("•-*")

        # 1. Degree detection
        if not degree:
            for pat in DEGREE_PATTERNS:
                m = pat.search(clean)
                if m:
                    # If line is mostly the degree e.g. "Bachelor of Computer Applications (BCA)"
                    degree = clean
                    break

        # 2. Institution detection
        if any(k in clean.lower() for k in INSTITUTION_KEYWORDS):
            inst, loc = split_institution_and_location(clean)
            if not institution:
                institution = inst
            if loc and not location:
                location = loc

    # If institution not found with keywords, check lines that aren't degree or dates
    if not institution:
        for line in entry_lines:
            clean = line.strip().strip("•-*")
            if clean != degree and not YEAR_RANGE_REGEX.search(clean) and not clean.isdigit():
                institution = clean
                break

    return EducationItem(
        degree=degree,
        institution=institution,
        location=location,
        start_year=start_year,
        end_year=end_year,
    )
