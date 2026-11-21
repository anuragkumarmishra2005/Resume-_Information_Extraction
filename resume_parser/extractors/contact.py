"""Contact information extractor.

Extracts candidate name, emails, phones, links, and location from the
document header and body using heuristics, regex, phonenumbers, and spaCy NER.
"""

import logging
import re
from typing import List, Optional, Set, Tuple
import phonenumbers
from phonenumbers import PhoneNumberMatcher, PhoneNumberFormat
import spacy

from resume_parser.models import PersonalData, PersonalLinks

logger = logging.getLogger(__name__)

# Load spacy model lazily
_nlp = None


def get_spacy_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning("Failed to load en_core_web_sm: %s", e)
            _nlp = None
    return _nlp


# Regex patterns
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Common URL patterns (including schemeless github.com/..., linkedin.com/...)
URL_REGEX = re.compile(
    r"(?:https?://|www\.)[^\s,;\"'<>]+|(?:(?:github\.com|linkedin\.com|leetcode\.com|geeksforgeeks\.org|gitlab\.com|bitbucket\.org|kaggle\.com|medium\.com|x\.com|twitter\.com)/[^\s,;\"'<>]+)",
    re.IGNORECASE,
)

# Phone regex for initial candidate detection
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}(?:[\s.-]?\d{1,5})?"
)

INVALID_NAME_WORDS = {
    "resume",
    "curriculum",
    "vitae",
    "cv",
    "biodata",
    "profile",
    "contact",
    "summary",
    "experience",
    "education",
    "skills",
    "projects",
    "email",
    "phone",
    "address",
    "page",
}


def extract_emails(text: str, document_links: Optional[List[str]] = None) -> List[str]:
    """Extract and deduplicate email addresses."""
    emails: List[str] = []
    seen: Set[str] = set()

    # From text
    for match in EMAIL_REGEX.findall(text):
        cleaned = match.strip().rstrip(".,;")
        lower = cleaned.lower()
        if lower not in seen:
            seen.add(lower)
            emails.append(cleaned)

    # From document hyperlinks (e.g. mailto:...)
    if document_links:
        for link in document_links:
            if link.lower().startswith("mailto:"):
                raw_mail = link[7:].split("?")[0].strip()
                if EMAIL_REGEX.match(raw_mail):
                    lower = raw_mail.lower()
                    if lower not in seen:
                        seen.add(lower)
                        emails.append(raw_mail)

    return emails


def extract_phones(text: str) -> List[str]:
    """Extract and normalize phone numbers using phonenumbers."""
    normalized_phones: List[str] = []
    seen_digits: Set[str] = set()

    def process_number(num_str: str, default_region: Optional[str] = None):
        try:
            parsed = phonenumbers.parse(num_str, default_region)
            if phonenumbers.is_possible_number(parsed) or phonenumbers.is_valid_number(parsed):
                digits = re.sub(r"\D", "", phonenumbers.format_number(parsed, PhoneNumberFormat.E164))
                if len(digits) >= 10 and digits not in seen_digits:
                    seen_digits.add(digits)
                    # Normalize format
                    if parsed.country_code == 91:
                        # Indian phone number: +91 7827349893
                        formatted = f"+91 {parsed.national_number}"
                    elif parsed.country_code == 1:
                        # North American number
                        nat = str(parsed.national_number).zfill(10)
                        formatted = f"({nat[:3]}) {nat[3:6]}-{nat[6:]}"
                    else:
                        formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
                    normalized_phones.append(formatted)
        except Exception:
            pass

    # 1. Match with PhoneNumberMatcher across regions
    for region in ["IN", "US", "GB", None]:
        try:
            for match in PhoneNumberMatcher(text, region):
                process_number(match.raw_string, region)
        except Exception:
            continue

    # 2. Regex fallback for numbers like +91 7827349893 that might have unusual separators
    candidates = PHONE_REGEX.findall(text)
    for cand in candidates:
        cand_clean = cand.strip().strip("-,;|")
        # Ensure it has at least 10 digits and not just a year (e.g., 2024 - 2025)
        digits_only = re.sub(r"\D", "", cand_clean)
        if 10 <= len(digits_only) <= 15:
            # Check not year range
            if not re.match(r"^(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}$", cand_clean):
                process_number(cand_clean, "IN")
                process_number(cand_clean, "US")

    return normalized_phones


def extract_links(text: str, document_links: Optional[List[str]] = None) -> PersonalLinks:
    """Extract social, portfolio, and code repository links."""
    links = PersonalLinks()
    other_links: List[str] = []
    seen_lower: Set[str] = set()

    all_raw_urls: List[str] = []

    # From document hyperlinks
    if document_links:
        for dl in document_links:
            if not dl.lower().startswith("mailto:"):
                all_raw_urls.append(dl)

    # From text regex
    for match in URL_REGEX.finditer(text):
        url = match.group(0).strip().rstrip(".,;|)]}")
        all_raw_urls.append(url)

    for url in all_raw_urls:
        clean_url = url.strip().rstrip("/")
        lower_url = clean_url.lower()

        # Deduplicate
        norm_key = re.sub(r"^https?://(?:www\.)?", "", lower_url)
        if norm_key in seen_lower:
            continue
        seen_lower.add(norm_key)

        if "linkedin.com" in lower_url:
            if not links.linkedin:
                links.linkedin = clean_url
            # If links.linkedin already exists, do not duplicate into other_links unless different domain
        elif "github.com" in lower_url:
            if not links.github:
                links.github = clean_url
            # Same for github
        else:
            other_links.append(clean_url)

    links.other = other_links
    return links


def extract_location(header_text: str, full_text: str) -> Optional[str]:
    """Extract candidate location (city, state, country)."""
    # Look at header lines first (split by pipes, bullets, dashes, commas)
    header_lines = [line.strip() for line in header_text.splitlines() if line.strip()]

    # Known Indian/International cities & states patterns
    location_pattern = re.compile(
        r"\b(?:[A-Z][a-zA-Z\s.-]+,\s*(?:[A-Z][a-zA-Z\s.-]+,\s*)?[A-Z][a-zA-Z\s.-]+)\b"
    )

    for line in header_lines[:5]:
        # Split line on pipe or bullet
        tokens = re.split(r"[|•·]", line)
        for token in tokens:
            t = token.strip().rstrip(",")
            if not t:
                continue
            # If token contains email, phone, or URL, skip
            if EMAIL_REGEX.search(t) or PHONE_REGEX.search(t) or URL_REGEX.search(t):
                continue
            # If token looks like a location e.g. "New Delhi, India" or "San Francisco, CA"
            if "," in t and len(t.split(",")) <= 4 and len(t) <= 60:
                # Validate with spaCy or city keywords
                nlp = get_spacy_nlp()
                if nlp:
                    doc = nlp(t)
                    if any(ent.label_ in ("GPE", "LOC") for ent in doc.ents):
                        return t
                return t

    # Fallback with spaCy on header
    nlp = get_spacy_nlp()
    if nlp and header_text:
        doc = nlp(header_text)
        gpes = [ent.text.strip() for ent in doc.ents if ent.label_ in ("GPE", "LOC")]
        if gpes:
            # Combine adjacent or return the best
            for gpe in gpes:
                if len(gpe) > 2 and not any(w in gpe.lower() for w in INVALID_NAME_WORDS):
                    return gpe

    return None


def extract_name(
    header_text: str,
    top_large_text: Optional[List[str]] = None,
    emails: Optional[List[str]] = None,
    phones: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> Optional[str]:
    """Extract candidate full name using font heuristics, top-line position, and spaCy NER."""
    # 1. Check top large font text (most reliable signal from PDF layout)
    if top_large_text:
        for cand in top_large_text:
            cleaned = re.sub(r"[|•·\-_]", "", cand).strip()
            # Must not be email, url, phone, or generic heading
            if (
                cleaned
                and len(cleaned.split()) in (2, 3, 4)
                and not EMAIL_REGEX.search(cleaned)
                and not URL_REGEX.search(cleaned)
                and not any(w in cleaned.lower().split() for w in INVALID_NAME_WORDS)
            ):
                return cleaned

    # 2. Check first non-empty lines in header
    lines = [line.strip() for line in header_text.splitlines() if line.strip()]
    for line in lines[:4]:
        # Strip trailing separators
        cleaned = re.sub(r"[|•·\-_,]+$", "", line).strip()
        # If line has separators like |, take first part
        parts = re.split(r"[|•·]", cleaned)
        first_part = parts[0].strip()

        # Reject if matches email, url, phone, or invalid word
        if (
            EMAIL_REGEX.search(first_part)
            or URL_REGEX.search(first_part)
            or any(c.isdigit() for c in first_part)
        ):
            continue

        words = first_part.split()
        if 2 <= len(words) <= 4:
            lower_words = [w.lower() for w in words]
            if not any(w in INVALID_NAME_WORDS for w in lower_words):
                if location and first_part.lower() == location.lower():
                    continue
                return first_part

    # 3. Fallback: spaCy PERSON entity in header
    nlp = get_spacy_nlp()
    if nlp and header_text:
        doc = nlp(header_text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                cleaned = ent.text.strip()
                words = cleaned.split()
                if 2 <= len(words) <= 4 and not any(c.isdigit() for c in cleaned):
                    if not any(w.lower() in INVALID_NAME_WORDS for w in words):
                        if location and cleaned.lower() == location.lower():
                            continue
                        return cleaned

    return None


def extract_contact_info(
    header_text: str,
    full_text: str,
    document_links: Optional[List[str]] = None,
    top_large_text: Optional[List[str]] = None,
) -> PersonalData:
    """Extract complete PersonalData structure."""
    emails = extract_emails(full_text, document_links)
    phones = extract_phones(header_text or full_text)
    links = extract_links(full_text, document_links)
    location = extract_location(header_text, full_text)
    name = extract_name(header_text, top_large_text, emails, phones, location)

    return PersonalData(
        name=name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
    )
