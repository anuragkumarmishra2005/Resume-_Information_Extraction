"""Skills extractor.

Extracts technical, conceptual, and soft skills from the resume,
preserving categories when explicitly grouped and matching against
a curated taxonomy of 400+ skills with RapidFuzz.
"""

import csv
import logging
import os
import re
from typing import Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz, process

from resume_parser.models import SkillsData

logger = logging.getLogger(__name__)

TAXONOMY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "skills.csv"
)

# In-memory taxonomy cache
_TAXONOMY: Optional[Dict[str, str]] = None  # lower_skill -> canonical_name
_TAXONOMY_CATEGORIES: Optional[Dict[str, str]] = None  # canonical_name -> category
_CANONICAL_LIST: Optional[List[str]] = None


def load_taxonomy(csv_path: str = TAXONOMY_PATH) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    """Load skills taxonomy from CSV."""
    global _TAXONOMY, _TAXONOMY_CATEGORIES, _CANONICAL_LIST
    if _TAXONOMY is not None:
        return _TAXONOMY, _TAXONOMY_CATEGORIES, _CANONICAL_LIST

    taxonomy = {}
    categories = {}
    canonical_list = []

    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                skill = row.get("skill", "").strip()
                cat = row.get("category", "").strip()
                if skill:
                    taxonomy[skill.lower()] = skill
                    categories[skill] = cat
                    canonical_list.append(skill)
    else:
        logger.warning("Taxonomy file not found at %s", csv_path)

    _TAXONOMY = taxonomy
    _TAXONOMY_CATEGORIES = categories
    _CANONICAL_LIST = canonical_list
    return _TAXONOMY, _TAXONOMY_CATEGORIES, _CANONICAL_LIST


def canonicalize_skill(raw_skill: str, taxonomy: Dict[str, str], canonical_list: List[str]) -> str:
    """Match a raw skill string to its canonical taxonomy form using exact and fuzzy matching."""
    cleaned = raw_skill.strip().strip("•-*·,;")
    if not cleaned:
        return ""

    lower = cleaned.lower()
    # 1. Exact case-insensitive match
    if lower in taxonomy:
        return taxonomy[lower]

    # 2. Match without parenthetical notes like "Machine Learning (Beginner)"
    base = re.sub(r"\s*\([^)]*\)", "", cleaned).strip()
    if base.lower() in taxonomy:
        return taxonomy[base.lower()]

    # 3. High-threshold RapidFuzz match
    if canonical_list:
        match = process.extractOne(
            base,
            canonical_list,
            scorer=fuzz.ratio,
            score_cutoff=90,
        )
        if match:
            return match[0]

    return cleaned


def split_skill_tokens(line: str) -> List[str]:
    """Split a comma/bullet separated line of skills into individual tokens."""
    # Split on commas, vertical bars, or semicolons
    raw_tokens = re.split(r"[,|;•·\t]+", line)
    cleaned_tokens: List[str] = []
    for t in raw_tokens:
        tok = t.strip()
        # Remove leading bullet
        tok = re.sub(r"^[•\-\*]\s*", "", tok).strip()
        if tok and len(tok) <= 50 and not tok.startswith(("http", "www")):
            cleaned_tokens.append(tok)
    return cleaned_tokens


def extract_skills(skills_text: str, full_text: str) -> SkillsData:
    """Extract categorized and aggregated skills from resume text.

    Args:
        skills_text: Content from the designated SKILLS section.
        full_text: Full document text.

    Returns:
        SkillsData object with `all` and `by_category`.
    """
    taxonomy, categories, canonical_list = load_taxonomy()

    by_category: Dict[str, List[str]] = {}
    all_skills_set: Set[str] = set()
    all_skills_ordered: List[str] = []

    def add_skill(skill_name: str, cat_name: Optional[str] = None):
        if not skill_name:
            return
        canon = canonicalize_skill(skill_name, taxonomy, canonical_list)
        if not canon:
            return

        if cat_name:
            if cat_name not in by_category:
                by_category[cat_name] = []
            if canon not in by_category[cat_name]:
                by_category[cat_name].append(canon)

        if canon.lower() not in [s.lower() for s in all_skills_set]:
            all_skills_set.add(canon)
            all_skills_ordered.append(canon)

    # 1. Parse categorized lines in the skills section
    category_regex = re.compile(
        r"^[•\-\*\s]*([A-Za-z0-9\s/&+-]{2,35})\s*:\s*(.+)$"
    )

    # Preprocess lines to combine multiline wrapped entries
    raw_lines = skills_text.splitlines() if skills_text else full_text.splitlines()
    merged_lines: List[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Check if line starts a new bullet or new category
        if category_regex.match(stripped) or stripped.startswith(("•", "*", "-")):
            merged_lines.append(stripped)
        elif merged_lines:
            # Continuation line of previous category or bullet
            merged_lines[-1] = merged_lines[-1] + " " + stripped
        else:
            merged_lines.append(stripped)

    for line in merged_lines:
        cat_match = category_regex.match(line)
        if cat_match:
            category_label = cat_match.group(1).strip()
            skills_payload = cat_match.group(2).strip()

            tokens = split_skill_tokens(skills_payload)
            for token in tokens:
                add_skill(token, category_label)
        elif skills_text:
            # Line without explicit category under Skills heading
            tokens = split_skill_tokens(line)
            for token in tokens:
                add_skill(token, None)

    # 2. Also scan entire document or skills section against taxonomy for any unlisted core skills
    # (Only scan in skills_text if present, otherwise across full_text)
    text_to_scan = skills_text if skills_text else full_text
    lower_scan = f" {text_to_scan.lower()} "

    for skill_lower, canonical in taxonomy.items():
        # Match as word boundary
        pattern = r"(?<![a-zA-Z0-9_])" + re.escape(skill_lower) + r"(?![a-zA-Z0-9_])"
        if re.search(pattern, lower_scan):
            add_skill(canonical, None)

    return SkillsData(
        all=all_skills_ordered,
        by_category=by_category,
    )
