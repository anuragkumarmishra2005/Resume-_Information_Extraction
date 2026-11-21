"""Projects extractor.

Extracts project name, technology stack (even when embedded on the same line),
and bullet-point descriptions.
"""

import logging
import re
from typing import List, Optional, Tuple
from resume_parser.extractors.skills import canonicalize_skill, load_taxonomy
from resume_parser.models import ProjectItem

logger = logging.getLogger(__name__)


def is_bullet_line(line: str) -> bool:
    """Check if line is a bullet point."""
    stripped = line.strip()
    return bool(stripped.startswith(("•", "*", "- ", "– ", "+ ")) or stripped.startswith("•"))


def split_project_header(header_line: str) -> Tuple[Optional[str], List[str]]:
    """Separate project name and technology stack from a single header line.

    Handles inline stacks like:
    - 'Chat Buddy AI - AI Chatbot Application React JS, TypeScript, Vite, Groq API, Tailwind CSS'
    - 'Student Performance Prediction App Python, scikit-learn, Streamlit, pandas'
    - 'Music Streaming App (Spotify-Inspired) Python, Flask, JavaScript, MySQL, HTML/CSS'
    - 'Portfolio Website | Next.js, Tailwind CSS, Vercel'
    - 'Task Tracker (React, Redux, Firebase)'
    """
    cleaned = header_line.strip().strip("•-*")
    if not cleaned:
        return None, []

    taxonomy, _, canonical_list = load_taxonomy()

    # 1. Pipe-delimited or colon-delimited tech stack
    # e.g. "Project Name | Python, Django, PostgreSQL" or "Project Name: React, Node.js"
    if "|" in cleaned:
        parts = [p.strip() for p in cleaned.split("|") if p.strip()]
        if len(parts) >= 2:
            name = parts[0]
            techs = _parse_tech_tokens(parts[1], taxonomy, canonical_list)
            return name, techs

    if re.search(r"\b(?:Technologies|Tech Stack|Built with|Tools):\s*(.+)$", cleaned, re.IGNORECASE):
        m = re.search(r"^(.*?)(?:\s*(?:Technologies|Tech Stack|Built with|Tools):\s*)(.+)$", cleaned, re.IGNORECASE)
        if m:
            name = m.group(1).strip().rstrip("|-–— ")
            techs = _parse_tech_tokens(m.group(2), taxonomy, canonical_list)
            return name, techs

    # 2. Parenthesized tech stack e.g. "E-Commerce App (React, Node.js, MongoDB)"
    paren_match = re.search(r"^(.*?)\s*\(([^)]+)\)\s*$", cleaned)
    if paren_match:
        name_cand = paren_match.group(1).strip()
        inside = paren_match.group(2).strip()
        if "," in inside or any(tok.strip().lower() in taxonomy for tok in inside.split()):
            techs = _parse_tech_tokens(inside, taxonomy, canonical_list)
            return name_cand, techs

    # 3. Comma-separated tail of known technologies
    comma_idx = cleaned.find(",")
    if comma_idx != -1:
        prefix_before_comma = cleaned[:comma_idx]
        parts_before = prefix_before_comma.split()
        split_point = len(prefix_before_comma)

        for i in range(len(parts_before) - 1, -1, -1):
            cand = " ".join(parts_before[i:])
            cand_clean = re.sub(r"^[–—\-|\s]+", "", cand).strip()
            if cand_clean.lower() in taxonomy or any(
                k in cand_clean.lower()
                for k in [
                    "react",
                    "python",
                    "java",
                    "node",
                    "flask",
                    "django",
                    "c++",
                    "typescript",
                    "javascript",
                    "sql",
                    "html",
                    "css",
                    "vue",
                    "angular",
                ]
            ):
                split_point = cleaned.find(cand, len(" ".join(parts_before[:i])))
                break

        name = cleaned[:split_point].strip().rstrip("|–—-( ")
        techs_str = cleaned[split_point:].strip().lstrip("|–—-) ")
        techs = _parse_tech_tokens(techs_str, taxonomy, canonical_list)
        return name, techs

    # 4. Default: entire line is project name
    return cleaned, []


def _parse_tech_tokens(techs_str: str, taxonomy: dict, canonical_list: list) -> List[str]:
    """Parse and canonicalize comma-separated technology strings."""
    tokens = [t.strip().strip("()[]") for t in re.split(r"[,/|;]+", techs_str) if t.strip()]
    canonical_techs: List[str] = []
    for tok in tokens:
        c = canonicalize_skill(tok, taxonomy, canonical_list)
        if c and c not in canonical_techs:
            canonical_techs.append(c)
    return canonical_techs


def is_continuation_line(line: str) -> bool:
    """Check if a non-bullet line is actually a continuation of the previous bullet point."""
    stripped = line.strip()
    if not stripped:
        return False
    # If starts with lowercase letter
    if stripped[0].islower():
        return True
    words = stripped.split()
    # Very short lines ending in punctuation e.g. 'responses.', 'expressions.', 'JavaScript.'
    if len(words) <= 2 and stripped.endswith((".", ";", ",")):
        return True
    if len(words) <= 3 and not ("," in stripped or "|" in stripped or "–" in stripped) and stripped.endswith("."):
        return True
    return False


def extract_projects(projects_text: str, non_job_blocks: Optional[List[dict]] = None) -> List[ProjectItem]:
    """Extract structured project items from the Projects section and any routed non-job blocks."""
    items: List[ProjectItem] = []
    lines = [l.rstrip() for l in projects_text.splitlines() if l.strip()]

    # Group into project entry blocks
    blocks: List[List[str]] = []
    current_block: List[str] = []
    in_bullets = False

    for line in lines:
        stripped = line.strip()
        is_bullet = is_bullet_line(stripped)

        if in_bullets and not is_bullet:
            if is_continuation_line(stripped):
                current_block.append(line)
            else:
                # Start of a new project
                if current_block:
                    blocks.append(current_block)
                current_block = [line]
                in_bullets = False
        else:
            if is_bullet:
                in_bullets = True
            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    for block in blocks:
        item = _parse_project_block(block)
        if item and (item.name or item.description):
            items.append(item)

    # Also include any non-job blocks routed from experience (e.g. Personal & Academic Projects)
    if non_job_blocks:
        for nj in non_job_blocks:
            header = re.sub(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}\b", "", nj.get("header", "")).strip()
            name, techs = split_project_header(header)
            items.append(
                ProjectItem(
                    name=name or header,
                    technologies=techs,
                    description=nj.get("bullets", []),
                )
            )

    return items


def _parse_project_block(block_lines: List[str]) -> ProjectItem:
    """Parse a single block representing one project."""
    header_lines: List[str] = []
    description: List[str] = []
    current_bullet: Optional[str] = None

    for line in block_lines:
        stripped = line.strip()
        if is_bullet_line(stripped):
            if current_bullet:
                description.append(current_bullet)
            current_bullet = re.sub(r"^[\s•\-\*\+–]+\s*", "", stripped).strip()
        elif current_bullet is not None:
            # Continuation line
            current_bullet += " " + stripped
        else:
            header_lines.append(stripped)

    if current_bullet:
        description.append(current_bullet)

    if not header_lines:
        return ProjectItem(description=description)

    # First header line is project title + inline technologies
    main_header = header_lines[0]
    name, technologies = split_project_header(main_header)

    # If second header line has technologies and first did not
    if len(header_lines) > 1 and not technologies:
        _, sub_techs = split_project_header(header_lines[1])
        if sub_techs:
            technologies = sub_techs

    return ProjectItem(
        name=name,
        technologies=technologies,
        description=description,
    )
