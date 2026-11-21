"""Unit tests for education extractor (degree matching, dates, null handling)."""

from resume_parser.extractors.education import extract_education, parse_education_dates


def test_date_range_parsing():
    start, end = parse_education_dates("Graduated 2018 - 2022 from MIT")
    assert start == "2018"
    assert end == "2022"

    start, end = parse_education_dates("August 2020 to Present")
    assert start == "2020"
    assert end.lower() == "present"

    # Single graduation year
    start, end = parse_education_dates("Class of 2023")
    assert start is None
    assert end == "2023"

    # No dates
    start, end = parse_education_dates("Bachelor of Science in Physics")
    assert start is None
    assert end is None


def test_education_item_extraction():
    edu_text = """
    Bachelor of Science in Computer Science
    University of California, Berkeley, Berkeley, CA
    2018 - 2022

    Master of Science in Artificial Intelligence
    Stanford University, Stanford, CA
    2022 - 2024
    """
    items = extract_education(edu_text)
    assert len(items) == 2

    assert "Bachelor of Science" in items[0].degree
    assert "University of California" in items[0].institution
    assert items[0].start_year == "2018"
    assert items[0].end_year == "2022"

    assert "Master of Science" in items[1].degree
    assert "Stanford University" in items[1].institution
    assert items[1].start_year == "2022"
    assert items[1].end_year == "2024"


def test_education_missing_dates_remains_null():
    edu_text = """
    Bachelor of Computer Applications (BCA)
    KR Mangalam University, Gurugram, Haryana, India
    """
    items = extract_education(edu_text)
    assert len(items) == 1
    assert "Bachelor of Computer Applications" in items[0].degree
    assert "KR Mangalam University" in items[0].institution
    assert items[0].start_year is None
    assert items[0].end_year is None
