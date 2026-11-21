"""Unit tests for experience extractor (multi-line headers, date formats, non-job filtering)."""

from resume_parser.extractors.experience import extract_experience, parse_date_and_location


def test_experience_date_formats():
    cases = [
        ("Software Engineer | Jan 2023 - Present | Remote", "Jan 2023", "Present", "Remote"),
        ("Data Analyst June 2021 – December 2022, London, UK", "June 2021", "December 2022", "London, UK"),
        ("Frontend Developer 06/2022 to 08/2023", "06/2022", "08/2023", None),
        ("Backend Lead 2020 - 2024", "2020", "2024", None),
    ]
    for text, exp_s, exp_e, exp_loc in cases:
        s, e, loc, _ = parse_date_and_location(text)
        assert s == exp_s
        assert e == exp_e
        if exp_loc:
            assert loc == exp_loc


def test_experience_multi_line_and_bullet_wrapping():
    exp_text = """
    Software Engineer
    Google Inc., Mountain View, CA
    Jan 2022 - Present
    • Built scalable distributed storage pipelines handling 10M events per second
      with under 5ms latency across multi-region clusters.
    • Collaborated with product teams to roll out new real-time analytics.

    Junior Developer
    Microsoft, Redmond, WA
    2020 - 2022
    • Developed internal web portals using TypeScript and React.
    """
    items, non_jobs = extract_experience(exp_text)
    assert len(items) == 2

    assert items[0].title == "Software Engineer"
    assert "Google" in items[0].organization
    assert items[0].start_date == "Jan 2022"
    assert items[0].end_date == "Present"
    assert len(items[0].description) == 2
    # Verify wrapped line was appended
    assert "with under 5ms latency" in items[0].description[0]

    assert items[1].title == "Junior Developer"
    assert "Microsoft" in items[1].organization


def test_non_job_block_filtered():
    exp_text = """
    Robotics Intern June 2024 - Aug 2024
    Acme Robotics
    • Built robot prototypes.

    Personal & Academic Projects 2023 - 2024
    • Designed a toy compiler in C++.
    • Participated in college lab projects.
    """
    items, non_jobs = extract_experience(exp_text)
    assert len(items) == 1
    assert items[0].title == "Robotics Intern"
    assert len(non_jobs) == 1
    assert "Personal & Academic Projects" in non_jobs[0]["header"]
