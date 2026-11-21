"""Unit tests for JSON and CSV exporters."""

import json
from resume_parser.exporters import (
    export_to_json,
    export_candidates_to_csv,
    export_relational_csvs,
)
from resume_parser.models import (
    EducationItem,
    ExperienceItem,
    MetaData,
    PersonalData,
    PersonalLinks,
    ProjectItem,
    ResumeData,
    SkillsData,
)


def create_sample_resume() -> ResumeData:
    return ResumeData(
        personal=PersonalData(
            name="Alice Johnson",
            emails=["alice@example.com"],
            phones=["+1 (555) 019-2834"],
            location="Seattle, WA",
            links=PersonalLinks(
                linkedin="https://linkedin.com/in/alicej",
                github="https://github.com/alicej",
                other=["https://alice.dev"],
            ),
        ),
        summary="Experienced software engineer with deep cloud expertise.",
        skills=SkillsData(
            all=["Python", "Go", "Docker", "AWS"],
            by_category={"Languages": ["Python", "Go"], "Cloud": ["Docker", "AWS"]},
        ),
        education=[
            EducationItem(
                degree="B.S. in Computer Science",
                institution="University of Washington",
                location="Seattle, WA",
                start_year="2016",
                end_year="2020",
            )
        ],
        experience=[
            ExperienceItem(
                title="Cloud Architect",
                organization="CloudCorp",
                start_date="2020",
                end_date="Present",
                location="Seattle, WA",
                description=["Designed AWS architectures."],
            )
        ],
        projects=[
            ProjectItem(
                name="Serverless Auth",
                technologies=["Python", "AWS Lambda"],
                description=["Built OAuth microservice."],
            )
        ],
        achievements=["AWS Certified Solutions Architect"],
        meta=MetaData(source_file="sample.pdf", pages=1, extraction_time_ms=120, warnings=[]),
    )


def test_export_to_json_conforms_to_schema():
    sample = create_sample_resume()
    json_str = export_to_json(sample)
    d = json.loads(json_str)

    assert d["personal"]["name"] == "Alice Johnson"
    assert d["personal"]["emails"] == ["alice@example.com"]
    assert d["personal"]["phones"] == ["+1 (555) 019-2834"]
    assert d["personal"]["links"]["linkedin"] == "https://linkedin.com/in/alicej"
    assert d["skills"]["by_category"]["Languages"] == ["Python", "Go"]
    assert len(d["education"]) == 1
    assert len(d["experience"]) == 1
    assert len(d["projects"]) == 1
    assert d["achievements"] == ["AWS Certified Solutions Architect"]
    assert d["meta"]["pages"] == 1


def test_export_to_csv():
    sample = create_sample_resume()
    csv_str = export_candidates_to_csv(sample)

    assert "Alice Johnson" in csv_str
    assert "alice@example.com" in csv_str
    assert "Python; Go" in csv_str
    assert "CloudCorp" in csv_str


def test_export_relational_csvs():
    sample = create_sample_resume()
    edu_csv, exp_csv, proj_csv = export_relational_csvs(sample)

    assert "University of Washington" in edu_csv
    assert "CloudCorp" in exp_csv
    assert "Serverless Auth" in proj_csv
