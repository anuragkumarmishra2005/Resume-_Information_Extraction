"""Unit tests for contact info extractor (email regex, phone normalization, URLs, location)."""

from resume_parser.extractors.contact import (
    extract_emails,
    extract_phones,
    extract_links,
    extract_location,
    extract_name,
)


def test_email_extraction_and_deduplication():
    text = """
    Reach out to john.doe@example.com or jdoe+work@sub.domain.org.
    Repeated: JOHN.DOE@EXAMPLE.COM should be deduplicated.
    Invalid: not-an-email, user@, @domain.com.
    """
    links = ["mailto:john.doe@example.com", "mailto:external@company.co.uk"]
    emails = extract_emails(text, links)

    assert "john.doe@example.com" in emails
    assert "jdoe+work@sub.domain.org" in emails
    assert "external@company.co.uk" in emails
    # Case deduplication
    assert len([e for e in emails if e.lower() == "john.doe@example.com"]) == 1


def test_phone_normalization_formats():
    text = """
    US Number: (555) 123-4567
    India Number: +91 7827349893
    UK Number: +44 20 7946 0958
    Another format: +1-555-987-6543
    Years that should not be parsed as phones: 2020 - 2024
    """
    phones = extract_phones(text)

    # Check India number
    assert any("+91 7827349893" in p or "78273" in p for p in phones)
    # Check US formats
    assert any("(555) 123-4567" in p or "555-123-4567" in p for p in phones)
    # Year range not parsed as phone
    assert not any("2020" in p and "2024" in p for p in phones)


def test_links_categorization():
    text = """
    LinkedIn: https://www.linkedin.com/in/sarah-connor-tech/
    GitHub: github.com/sarahconnor2024
    Portfolio: https://sarahconnor.dev
    LeetCode: leetcode.com/u/sarah_c
    """
    links = extract_links(text)

    assert links.linkedin == "https://www.linkedin.com/in/sarah-connor-tech"
    assert links.github == "github.com/sarahconnor2024"
    assert any("sarahconnor.dev" in l for l in links.other)
    assert any("leetcode.com" in l for l in links.other)


def test_location_and_name_separation():
    header = """
    Jane Smith
    San Francisco, CA | jane.smith@gmail.com | (555) 234-5678
    linkedin.com/in/janesmith | github.com/janesmith
    """
    name = extract_name(header)
    location = extract_location(header, header)

    assert name == "Jane Smith"
    assert location == "San Francisco, CA"
