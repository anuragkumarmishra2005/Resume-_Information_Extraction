"""Synthetic resume and ground truth generator.

Generates 25 diverse resumes (15 DOCX and 10 PDF) using Faker, python-docx,
and reportlab with varied section headers, date formats, layouts, and bullet styles.
For each resume, saves an exact ground-truth JSON conforming to the target schema.
"""

import json
import os
import random
from typing import Dict, List, Optional
from faker import Faker
import docx
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

fake = Faker()
Faker.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_resumes")
GT_DIR = os.path.join(BASE_DIR, "evaluation", "ground_truth")

os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(GT_DIR, exist_ok=True)

# Curated skill pools for realistic generation
SKILL_POOLS = {
    "Languages": ["Python", "Java", "C++", "JavaScript", "TypeScript", "Go", "SQL", "HTML", "CSS", "Rust"],
    "Frameworks & Libraries": ["React", "Django", "Flask", "FastAPI", "Spring Boot", "Next.js", "Express", "pandas", "scikit-learn", "Tailwind CSS"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite"],
    "Tools & Platforms": ["Git", "GitHub", "Docker", "Kubernetes", "Linux", "AWS", "Jira", "VS Code", "Jenkins"],
    "Concepts": ["OOP", "DSA", "REST APIs", "Microservices", "System Design", "CI/CD", "Agile", "Web Development"],
    "Soft Skills": ["Communication", "Problem Solving", "Team Collaboration", "Analytical Thinking", "Leadership"],
}

DEGREES = [
    "Bachelor of Science in Computer Science",
    "Bachelor of Technology in Information Technology",
    "Bachelor of Computer Applications (BCA)",
    "Master of Science in Software Engineering",
    "Master of Science in Data Science",
    "Master of Business Administration (MBA)",
    "Associate Degree in Computer Information Systems",
]

UNIVERSITIES = [
    ("Stanford University", "Stanford, CA"),
    ("University of California, Berkeley", "Berkeley, CA"),
    ("University of Texas at Austin", "Austin, TX"),
    ("University of Washington", "Seattle, WA"),
    ("Columbia University", "New York, NY"),
    ("Georgia Institute of Technology", "Atlanta, GA"),
    ("KR Mangalam University", "Gurugram, Haryana, India"),
    ("Indian Institute of Technology Delhi", "New Delhi, India"),
]

TITLES = [
    "Software Engineer",
    "Senior Backend Developer",
    "Full Stack Engineer",
    "Frontend Developer",
    "Data Scientist",
    "DevOps Engineer",
    "Cloud Solutions Architect",
    "Machine Learning Engineer",
]

COMPANIES = [
    ("Google LLC", "Mountain View, CA"),
    ("Microsoft Corporation", "Redmond, WA"),
    ("Amazon Web Services", "Seattle, WA"),
    ("Meta Platforms", "Menlo Park, CA"),
    ("Stripe Inc.", "San Francisco, CA"),
    ("Netflix", "Los Gatos, CA"),
    ("Salesforce", "San Francisco, CA"),
    ("Rotors Robotics", "New Delhi, India"),
]

HEADING_VARIANTS = {
    "summary": ["Profile", "Professional Summary", "About Me", "Career Objective", "Summary"],
    "education": ["Education", "Academic Background", "Educational Qualifications", "Education & Qualifications"],
    "skills": ["Technical Skills", "Skills", "Core Competencies", "Skills & Technologies"],
    "experience": ["Work Experience", "Professional Experience", "Employment History", "Experience", "Work History"],
    "projects": ["Projects", "Key Projects", "Featured Projects", "Technical Projects"],
    "achievements": ["Achievements", "Certifications & Awards", "Honors & Awards", "Certifications"],
}


def generate_candidate_data(idx: int) -> dict:
    """Generate realistic candidate dictionary and matching ground truth."""
    first = fake.first_name()
    last = fake.last_name()
    name = f"{first} {last}"
    username = f"{first.lower()}{last.lower()}{random.randint(10, 99)}"

    domain = random.choice(["gmail.com", "outlook.com", "example.com", "techmail.org"])
    email = f"{username}@{domain}"

    # Generate phone
    if random.choice([True, False]):
        # US phone
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
    else:
        # Indian phone
        phone = f"+91 {random.randint(70000, 99999)}{random.randint(10000, 99999)}"

    city = fake.city()
    state = fake.state_abbr()
    location = f"{city}, {state}"

    linkedin = f"https://linkedin.com/in/{username}"
    github = f"https://github.com/{username}"
    has_portfolio = random.choice([True, False])
    other_links = [f"https://{username}.dev"] if has_portfolio else []

    has_summary = random.choice([True, True, False])
    summary = (
        f"Experienced and detail-oriented {random.choice(TITLES).lower()} with a proven track record "
        f"of developing robust, high-performance software systems. Skilled in modern engineering workflows "
        f"and cross-functional team leadership."
        if has_summary
        else None
    )

    # Pick skills
    selected_categories = {}
    all_skills = []
    # Pick 3 to 5 categories
    cats_to_pick = random.sample(list(SKILL_POOLS.keys()), k=random.randint(3, 5))
    for cat in cats_to_pick:
        skills_in_cat = random.sample(SKILL_POOLS[cat], k=random.randint(3, 5))
        selected_categories[cat] = skills_in_cat
        for s in skills_in_cat:
            if s not in all_skills:
                all_skills.append(s)

    # Education (1 or 2)
    num_edu = random.choice([1, 2])
    education_list = []
    for _ in range(num_edu):
        deg = random.choice(DEGREES)
        inst, inst_loc = random.choice(UNIVERSITIES)
        has_dates = random.choice([True, True, False])
        if has_dates:
            s_year = str(random.randint(2014, 2020))
            e_year = str(int(s_year) + random.randint(3, 4))
        else:
            s_year, e_year = None, None
        education_list.append(
            {
                "degree": deg,
                "institution": inst,
                "location": inst_loc,
                "start_year": s_year,
                "end_year": e_year,
            }
        )

    # Experience (1 to 3)
    num_exp = random.randint(1, 3)
    experience_list = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
    for i in range(num_exp):
        title = random.choice(TITLES)
        company, comp_loc = random.choice(COMPANIES)
        s_yr = 2018 + i * 2
        e_yr = s_yr + 1
        s_date = f"{random.choice(months)} {s_yr}"
        e_date = "Present" if i == 0 and random.choice([True, False]) else f"{random.choice(months)} {e_yr}"

        bullets = [
            f"Spearheaded engineering development for cloud microservices achieving {random.randint(20, 90)}% performance improvement.",
            f"Engineered scalable REST APIs integrated with SQL and NoSQL database clusters.",
            f"Partnered with cross-functional product teams to deliver customer features ahead of schedule.",
        ]
        experience_list.append(
            {
                "title": title,
                "organization": company,
                "start_date": s_date,
                "end_date": e_date,
                "location": comp_loc,
                "description": bullets,
            }
        )

    # Projects (1 to 2)
    has_projects = random.choice([True, True, False])
    projects_list = []
    if has_projects:
        for p_idx in range(random.randint(1, 2)):
            p_name = f"{fake.word().capitalize()} {random.choice(['AI Platform', 'Analytics Dashboard', 'Cloud Tracker', 'Engine', 'App'])}"
            p_techs = random.sample(all_skills, k=min(4, len(all_skills)))
            p_bullets = [
                f"Developed full stack web application leveraging {', '.join(p_techs[:2])}.",
                f"Implemented automated CI/CD pipeline and integration tests with 95% code coverage.",
            ]
            projects_list.append(
                {
                    "name": p_name,
                    "technologies": p_techs,
                    "description": p_bullets,
                }
            )

    # Achievements (0 to 2)
    has_ach = random.choice([True, False])
    achievements_list = []
    if has_ach:
        achievements_list = [
            f"Certified {random.choice(['AWS Solutions Architect', 'Kubernetes Administrator', 'Google Cloud Engineer'])}",
            f"Winner of {random.randint(2021, 2025)} Regional Collegiate Hackathon",
        ]

    candidate = {
        "personal": {
            "name": name,
            "emails": [email],
            "phones": [phone],
            "location": location,
            "links": {
                "linkedin": linkedin,
                "github": github,
                "other": other_links,
            },
        },
        "summary": summary,
        "skills": {
            "all": all_skills,
            "by_category": selected_categories,
        },
        "education": education_list,
        "experience": experience_list,
        "projects": projects_list,
        "achievements": achievements_list,
        "meta": {
            "source_file": "",
            "pages": 1,
            "extraction_time_ms": 0,
            "warnings": [],
        },
    }
    return candidate


def write_docx_resume(candidate: dict, file_path: str):
    """Write candidate resume to a stylized DOCX document."""
    doc = docx.Document()

    # Style definitions
    p = candidate["personal"]
    bullet_symbol = random.choice(["•", "-", "*"])

    # Header
    name_p = doc.add_paragraph()
    name_run = name_p.add_run(p["name"])
    name_run.bold = True
    name_run.font.size = Pt(20)
    name_run.font.color.rgb = RGBColor(30, 41, 59)

    contact_parts = [p["location"]] + p["emails"] + p["phones"]
    contact_p = doc.add_paragraph(" | ".join(contact_parts))
    contact_p.paragraph_format.space_after = Pt(4)

    links_p = doc.add_paragraph()
    links_list = []
    if p["links"]["github"]:
        links_list.append(p["links"]["github"])
    if p["links"]["linkedin"]:
        links_list.append(p["links"]["linkedin"])
    links_list.extend(p["links"]["other"])
    links_p.add_run(" | ".join(links_list))
    links_p.paragraph_format.space_after = Pt(12)

    # Decide section order
    section_keys = ["summary", "skills", "experience", "education", "projects", "achievements"]
    if random.choice([True, False]):
        # Swap education and experience
        section_keys = ["summary", "education", "skills", "experience", "projects", "achievements"]

    for sec in section_keys:
        if sec == "summary" and candidate["summary"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["summary"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            doc.add_paragraph(candidate["summary"])

        elif sec == "skills" and candidate["skills"]["all"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["skills"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            by_cat = candidate["skills"]["by_category"]
            if by_cat and random.choice([True, True, False]):
                for cat, sk_list in by_cat.items():
                    doc.add_paragraph(f"{bullet_symbol} {cat}: {', '.join(sk_list)}")
            else:
                doc.add_paragraph(f"{bullet_symbol} {', '.join(candidate['skills']['all'])}")

        elif sec == "education" and candidate["education"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["education"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            for edu in candidate["education"]:
                dates = f" | {edu['start_year']} - {edu['end_year']}" if edu["start_year"] else ""
                doc.add_paragraph(f"{edu['degree']}{dates}")
                doc.add_paragraph(f"{edu['institution']}, {edu['location']}")

        elif sec == "experience" and candidate["experience"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["experience"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            for exp in candidate["experience"]:
                # Multi-attribute header
                doc.add_paragraph(f"{exp['title']} | {exp['start_date']} - {exp['end_date']} | {exp['location']}")
                doc.add_paragraph(exp["organization"])
                for b in exp["description"]:
                    doc.add_paragraph(f"{bullet_symbol} {b}")

        elif sec == "projects" and candidate["projects"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["projects"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            for proj in candidate["projects"]:
                tech_str = f" {', '.join(proj['technologies'])}" if proj["technologies"] else ""
                doc.add_paragraph(f"{proj['name']}{tech_str}")
                for b in proj["description"]:
                    doc.add_paragraph(f"{bullet_symbol} {b}")

        elif sec == "achievements" and candidate["achievements"]:
            h = doc.add_paragraph()
            hrun = h.add_run(random.choice(HEADING_VARIANTS["achievements"]))
            hrun.bold = True
            hrun.font.size = Pt(13)
            for ach in candidate["achievements"]:
                doc.add_paragraph(f"{bullet_symbol} {ach}")

    doc.save(file_path)


def write_pdf_resume(candidate: dict, file_path: str):
    """Write candidate resume to a stylized PDF document using ReportLab."""
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    header_style = ParagraphStyle(
        "ResumeHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "ResumeSection",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2,
    )

    story = []
    p = candidate["personal"]
    bullet = "•"

    # Title & Contact
    story.append(Paragraph(p["name"], title_style))
    contact_line = " | ".join([p["location"]] + p["emails"] + p["phones"])
    story.append(Paragraph(contact_line, header_style))

    links_list = []
    if p["links"]["github"]:
        links_list.append(p["links"]["github"])
    if p["links"]["linkedin"]:
        links_list.append(p["links"]["linkedin"])
    links_list.extend(p["links"]["other"])
    story.append(Paragraph(" | ".join(links_list), header_style))
    story.append(Spacer(1, 6))

    # Summary
    if candidate["summary"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["summary"]), section_style))
        story.append(Paragraph(candidate["summary"], body_style))

    # Skills
    if candidate["skills"]["all"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["skills"]), section_style))
        by_cat = candidate["skills"]["by_category"]
        if by_cat:
            for cat, sk_list in by_cat.items():
                story.append(Paragraph(f"{bullet} <b>{cat}:</b> {', '.join(sk_list)}", body_style))
        else:
            story.append(Paragraph(f"{bullet} {', '.join(candidate['skills']['all'])}", body_style))

    # Education
    if candidate["education"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["education"]), section_style))
        for edu in candidate["education"]:
            dates = f" | {edu['start_year']} - {edu['end_year']}" if edu["start_year"] else ""
            story.append(Paragraph(f"<b>{edu['degree']}</b>{dates}", body_style))
            story.append(Paragraph(f"{edu['institution']}, {edu['location']}", body_style))

    # Experience
    if candidate["experience"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["experience"]), section_style))
        for exp in candidate["experience"]:
            hdr = f"<b>{exp['title']}</b> | {exp['start_date']} - {exp['end_date']} | {exp['location']}"
            story.append(Paragraph(hdr, body_style))
            story.append(Paragraph(exp["organization"], body_style))
            for b in exp["description"]:
                story.append(Paragraph(f"{bullet} {b}", body_style))

    # Projects
    if candidate["projects"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["projects"]), section_style))
        for proj in candidate["projects"]:
            tech_str = f" {', '.join(proj['technologies'])}" if proj["technologies"] else ""
            story.append(Paragraph(f"<b>{proj['name']}</b>{tech_str}", body_style))
            for b in proj["description"]:
                story.append(Paragraph(f"{bullet} {b}", body_style))

    # Achievements
    if candidate["achievements"]:
        story.append(Paragraph(random.choice(HEADING_VARIANTS["achievements"]), section_style))
        for ach in candidate["achievements"]:
            story.append(Paragraph(f"{bullet} {ach}", body_style))

    doc.build(story)


def main():
    print("Generating 25 synthetic resumes (15 DOCX and 10 PDF)...")

    # 15 DOCX files
    for i in range(1, 16):
        fname_base = f"synthetic_{i:02d}"
        candidate = generate_candidate_data(i)
        docx_path = os.path.join(SAMPLE_DIR, f"{fname_base}.docx")
        candidate["meta"]["source_file"] = f"{fname_base}.docx"

        write_docx_resume(candidate, docx_path)

        # Write ground truth JSON
        gt_path = os.path.join(GT_DIR, f"{fname_base}.docx.json")
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(candidate, f, indent=2)
        print(f"Generated DOCX: {docx_path}")

    # 10 PDF files
    for i in range(16, 26):
        fname_base = f"synthetic_{i:02d}"
        candidate = generate_candidate_data(i)
        pdf_path = os.path.join(SAMPLE_DIR, f"{fname_base}.pdf")
        candidate["meta"]["source_file"] = f"{fname_base}.pdf"

        write_pdf_resume(candidate, pdf_path)

        # Write ground truth JSON
        gt_path = os.path.join(GT_DIR, f"{fname_base}.pdf.json")
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(candidate, f, indent=2)
        print(f"Generated PDF:  {pdf_path}")

    # Also generate ground truth for Anurag's resume
    anurag_gt = {
        "personal": {
            "name": "Anurag Kumar Mishra",
            "emails": ["anuragkumarmishra414@gmail.com"],
            "phones": ["+91 7827349893"],
            "location": "New Delhi, India",
            "links": {
                "linkedin": "https://www.linkedin.com/in/anurag-kumar-mishra-8b47b63a6",
                "github": "https://github.com/anuragkumarmishra2005",
                "other": [
                    "https://leetcode.com/u/Anurag_Kumar_Mishra",
                    "https://geeksforgeeks.org/user/anuragkumarm9b5",
                ],
            },
        },
        "summary": "Motivated BCA student and aspiring software developer with hands-on experience in full-stack development, machine learning applications, and algorithmic problem solving. Proficient in Python and Java, with a passion for building real-world projects and continuously learning modern technologies.",
        "skills": {
            "all": [
                "Python", "Java", "C++", "SQL", "HTML", "CSS", "Flask", "pandas", "NumPy",
                "scikit-learn", "Streamlit", "Git", "GitHub", "MySQL", "Jupyter Notebook",
                "VS Code", "OOP", "DSA Fundamentals", "REST APIs", "Machine Learning",
                "Web Development", "Problem Solving", "Communication", "Team Collaboration",
                "Analytical Thinking"
            ],
            "by_category": {
                "Languages": ["Python", "Java", "C++", "SQL", "HTML", "CSS"],
                "Frameworks & Libraries": ["Flask", "pandas", "NumPy", "scikit-learn", "Streamlit"],
                "Tools & Platforms": ["Git", "GitHub", "MySQL", "Jupyter Notebook", "VS Code"],
                "Concepts": ["OOP", "DSA Fundamentals", "REST APIs", "Machine Learning", "Web Development", "Problem Solving"],
                "Soft Skills": ["Communication", "Team Collaboration", "Analytical Thinking", "Problem Solving"],
            },
        },
        "education": [
            {
                "degree": "Bachelor of Computer Applications (BCA)",
                "institution": "KR Mangalam University",
                "location": "Gurugram, Haryana, India",
                "start_year": None,
                "end_year": None,
            }
        ],
        "experience": [
            {
                "title": "Robotics Engineering Intern",
                "organization": "Rotors",
                "start_date": "June 2025",
                "end_date": "July 2025",
                "location": "India, Delhi",
                "description": [
                    "Designed a smart IoT-enabled livestock collar monitoring health metrics (temperature, heart rate) and GPS location for 100+ animals simultaneously with continuous data logging.",
                    "Integrated 5+ sensor modules, 2 microcontrollers, and Bluetooth communication systems achieving real-time data transmission with under 2-second latency across field conditions.",
                    "Collaborated with a 4-member multidisciplinary team to prototype, field-test, and present the fully functional device to company leadership, completing all deliverables within the internship timeframe.",
                ],
            }
        ],
        "projects": [
            {
                "name": "Chat Buddy AI - AI Chatbot Application",
                "technologies": ["React JS", "TypeScript", "Vite", "Groq API", "Tailwind CSS"],
                "description": [
                    "Built a sleek, ChatGPT-style web app using React 18, TypeScript, and Vite with Tailwind CSS and Framer Motion for a smooth, responsive UI.",
                    "Integrated Groq API (Llama 3.1) for ultra-fast AI inference using Server-Sent Events (SSE) streaming for instant responses.",
                    "Persisted chat history and API keys in localStorage so conversations survive page refreshes and no backend required.",
                    "Rendered rich AI responses with react-markdown and KaTeX, supporting formatted code blocks and mathematical expressions.",
                ],
            },
            {
                "name": "Student Performance Prediction App",
                "technologies": ["Python", "scikit-learn", "Streamlit", "pandas"],
                "description": [
                    "Preprocessed a student dataset by handling missing values, encoding categorical features, and normalizing data.",
                    "Trained and compared ML models (Logistic Regression, Random Forest, Decision Tree) to select the best performer.",
                    "Deployed an interactive Streamlit dashboard where users input student data and receive instant grade predictions.",
                    "Visualized feature importance and EDA insights to make results interpretable and user-friendly.",
                ],
            },
            {
                "name": "Music Streaming App (Spotify-Inspired)",
                "technologies": ["Python", "Flask", "JavaScript", "MySQL", "HTML", "CSS"],
                "description": [
                    "Designed a modern responsive UI with sidebar navigation, a persistent player bar, and playlist management inspired by Spotify.",
                    "Implemented audio playback controls: play/pause, next/previous track, volume slider, and dynamic seek bar using JavaScript.",
                    "Built a Flask REST backend with MySQL to manage users, songs, albums, playlists, and liked songs.",
                    "Added user authentication (register/login/logout) and a search feature to find songs and artists.",
                ],
            },
            {
                "name": "Personal & Academic Projects",
                "technologies": [],
                "description": [
                    "Applied programming knowledge through coursework, self-initiated projects, and online learning platforms.",
                    "Collaborated with peers to debug assignments, review code, and complete team-based lab projects.",
                ],
            },
        ],
        "achievements": [
            "Active competitive programmer on LeetCode and GeeksforGeeks, regularly solving DSA problems.",
            "Consistent GitHub activity with multiple project repositories showcasing practical development skills.",
            "Participated in inter-college coding events and online hackathons.",
        ],
        "meta": {
            "source_file": "AnuragMishra_resume_2026.pdf",
            "pages": 1,
            "extraction_time_ms": 0,
            "warnings": [],
        },
    }
    anurag_gt_path = os.path.join(GT_DIR, "AnuragMishra_resume_2026.pdf.json")
    with open(anurag_gt_path, "w", encoding="utf-8") as f:
        json.dump(anurag_gt, f, indent=2)
    print(f"Generated ground truth for real resume: {anurag_gt_path}")


if __name__ == "__main__":
    main()
