"""Work experience extractor.

Extracts job title, organization, dates, location, and bullet point descriptions.
Correctly handles multi-attribute header lines, company on following lines,
and filters out personal/academic project blocks from employment history.
"""

import logging
import re
from typing import List, Optional, Tuple
from resume_parser.models import ExperienceItem

logger = logging.getLogger(__name__)

DATE_RANGE_REGEX = re.compile(
    r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\d{4}|\d{1,2}/\d{4})\s*[-–—to\s]+\s*((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\d{4}|\d{1,2}/\d{4}|Present|Current|Ongoing|Now)\b",
    re.IGNORECASE,
)

COMMON_TITLE_KEYWORDS = [
    "engineer",
    "developer",
    "intern",
    "manager",
    "lead",
    "director",
    "analyst",
    "scientist",
    "consultant",
    "specialist",
    "architect",
    "designer",
    "administrator",
    "associate",
    "officer",
    "coordinator",
    "trainee",
    "fellow",
    "programmer",
    "technician",
    "executive",
    "researcher",
    "instructor",
    "professor",
]

NON_JOB_KEYWORDS = [
    "personal & academic projects",
    "personal and academic projects",
    "academic projects",
    "personal projects",
    "coursework",
    "academic coursework",
]


def is_non_job_block(text: str) -> bool:
    """Check if header or text denotes a project or coursework block rather than a job."""
    lower = text.lower()
    return any(njk in lower for njk in NON_JOB_KEYWORDS)


def is_bullet_line(line: str) -> bool:
    """Check if line is a bullet point or task description."""
    stripped = line.strip()
    return bool(stripped.startswith(("•", "*", "- ", "– ", "+ ")) or stripped.startswith("•"))


def parse_date_and_location(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Extract start_date, end_date, location, and remaining text."""
    m = DATE_RANGE_REGEX.search(text)
    if not m:
        return None, None, None, text

    start_d = m.group(1).strip()
    end_d = m.group(2).strip()

    before = text[: m.start()].strip().rstrip("|,-–—")
    after = text[m.end() :].strip().lstrip("|,-–—")

    location = None
    remaining = before

    if after:
        # After text is typically location (e.g. "India, Delhi" or "San Francisco, CA")
        location = after.strip().strip("|,; ")
    elif "|" in before:
        # Check if before text has pipe-delimited location
        parts = [p.strip() for p in before.split("|") if p.strip()]
        if len(parts) >= 2:
            remaining = parts[0]
            location = parts[-1]

    return start_d, end_d, location, remaining


def extract_experience(experience_text: str, full_text: str = "") -> Tuple[List[ExperienceItem], List[dict]]:
    """Extract structured experience items from the Experience section.

    Filters out personal/academic project blocks from experience.

    Returns:
        Tuple of (experience_items, non_job_project_blocks).
    """
    if not experience_text.strip():
        return [], []

    raw_lines = [line.rstrip() for line in experience_text.splitlines() if line.strip()]

    # Group lines into entry blocks
    # An entry starts with header lines (title, company, dates, location) followed by bullets
    entry_blocks: List[List[str]] = []
    current_block: List[str] = []
    in_bullets = False

    for line in raw_lines:
        stripped = line.strip()
        is_bullet = is_bullet_line(stripped)
        has_dates = bool(DATE_RANGE_REGEX.search(stripped))
        has_title_kw = any(k in stripped.lower() for k in COMMON_TITLE_KEYWORDS)

        # A new entry begins if we were already in bullets and hit a line with a date range or title
        # or if we encounter an explicit non-job block
        if in_bullets and (has_dates or (has_title_kw and not is_bullet and len(stripped.split()) <= 6) or is_non_job_block(stripped)):
            if current_block:
                entry_blocks.append(current_block)
            current_block = [line]
            in_bullets = False
        else:
            if is_bullet:
                in_bullets = True
            current_block.append(line)

    if current_block:
        entry_blocks.append(current_block)

    experience_items: List[ExperienceItem] = []
    non_job_blocks: List[dict] = []

    for block in entry_blocks:
        first_line = block[0] if block else ""
        if is_non_job_block(first_line) or (len(block) > 1 and is_non_job_block(" ".join(block[:2]))):
            # Capture as non-job project block (to avoid misreading as a job)
            logger.info("Filtered out non-job block from experience: %s", first_line)
            bullets = [
                re.sub(r"^[\s•\-\*\+–]+\s*", "", l).strip()
                for l in block
                if is_bullet_line(l)
            ]
            non_job_blocks.append({"header": first_line, "bullets": bullets})
            continue

        item = _parse_experience_block(block)
        if item and (item.title or item.organization):
            experience_items.append(item)

    return experience_items, non_job_blocks


def _parse_experience_block(block_lines: List[str]) -> ExperienceItem:
    """Parse a single block of lines for a work experience entry."""
    title: Optional[str] = None
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    description: List[str] = []

    header_lines: List[str] = []
    current_bullet: Optional[str] = None

    for line in block_lines:
        stripped = line.strip()
        if is_bullet_line(stripped):
            if current_bullet:
                description.append(current_bullet)
            current_bullet = re.sub(r"^[\s•\-\*\+–]+\s*", "", stripped).strip()
        elif current_bullet is not None:
            # Continuation of previous bullet
            current_bullet += " " + stripped
        else:
            header_lines.append(stripped)

    if current_bullet:
        description.append(current_bullet)

    if not header_lines:
        return ExperienceItem(description=description)

    # Analyze header lines (usually 1 or 2 lines)
    # Case A: Line 1 has Title + Date + Location, Line 2 has Company (e.g. Anurag's resume)
    # "Robotics Engineering Intern June 2025 - July 2025, India, Delhi"
    # "Rotors"
    for idx, hline in enumerate(header_lines):
        if DATE_RANGE_REGEX.search(hline):
            s_d, e_d, loc, remaining = parse_date_and_location(hline)
            if not start_date and s_d:
                start_date = s_d
                end_date = e_d
            if not location and loc:
                location = loc

            # If remaining has pipe or comma
            if remaining:
                parts = [p.strip() for p in re.split(r"[|,]", remaining) if p.strip()]
                if len(parts) >= 2:
                    # e.g. "Software Engineer | Google"
                    t_cand = parts[0]
                    org_cand = parts[1]
                    if any(k in t_cand.lower() for k in COMMON_TITLE_KEYWORDS):
                        title = t_cand
                        organization = org_cand
                    else:
                        organization = t_cand
                        title = org_cand
                else:
                    if any(k in remaining.lower() for k in COMMON_TITLE_KEYWORDS):
                        title = remaining
                    else:
                        organization = remaining
        else:
            # Line without date
            # Check if this line is organization or title
            clean_h = hline.strip().strip("•-*|,")
            if any(k in clean_h.lower() for k in COMMON_TITLE_KEYWORDS):
                if not title:
                    title = clean_h
                elif not organization:
                    organization = clean_h
            else:
                if not organization:
                    organization = clean_h
                elif not title:
                    title = clean_h

    # If organization is still not set and we have 2 header lines
    if not organization and len(header_lines) >= 2:
        for hl in header_lines:
            if hl != title and not DATE_RANGE_REGEX.search(hl):
                organization = hl
                break

    return ExperienceItem(
        title=title,
        organization=organization,
        start_date=start_date,
        end_date=end_date,
        location=location,
        description=description,
    )
