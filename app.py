"""Streamlit Web Application for Resume Information Extraction.

Provides an interactive GUI to upload resumes (PDF/DOCX), trigger extraction,
inspect structured sections, view raw text and diagnostics, and download JSON and CSV data.
"""

import io
import json
import os
import sys
from typing import Optional
import streamlit as st
import pandas as pd

# Ensure package root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from resume_parser.pipeline import parse_resume
from resume_parser.exporters import (
    export_to_json,
    export_candidates_to_csv,
    export_relational_csvs,
)
from resume_parser.extractors.text_extractor import extract_document
from resume_parser.models import ResumeData

st.set_page_config(
    page_title="Resume Information Extraction",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 2px 4px 2px 0;
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
    }
    .category-title {
        font-size: 1rem;
        font-weight: 600;
        color: #334155;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    .exp-card {
        border-left: 3px solid #3b82f6;
        padding-left: 12px;
        margin-bottom: 16px;
    }
    .proj-card {
        border-left: 3px solid #10b981;
        padding-left: 12px;
        margin-bottom: 16px;
    }
    .edu-card {
        border-left: 3px solid #8b5cf6;
        padding-left: 12px;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/resume.png", width=64)
    st.title("Resume Parser")
    st.markdown("Automated Resume Information Extraction pipeline powered by rule-based NLP and entity matching.")

    st.markdown("---")
    st.subheader("💡 Usage Instructions")
    st.markdown(
        """
        1. **Upload** a resume file in **PDF** or **DOCX** format.
        2. Validate the file size (maximum **10 MB**).
        3. Click the **Extract Information** button to start parsing.
        4. Browse structured information across the interactive tabs.
        5. Export parsed results as **JSON** or **CSV**.
        """
    )

    st.markdown("---")
    st.subheader("🔒 Privacy & Security")
    st.info(
        "All resume parsing and NLP analysis is performed **100% locally** in your memory space. "
        "No data is sent to external or cloud APIs, and no candidate information is retained or stored."
    )

    st.markdown("---")
    st.caption("Version 1.0.0 | Pure Python & Local NLP")

# Header Section
st.markdown('<div class="main-header">📄 Resume Information Extraction</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Convert unstructured resume documents into clean, validated, structured candidate data.</div>',
    unsafe_allow_html=True,
)

# Initialize Session State
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = None
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "source_filename" not in st.session_state:
    st.session_state.source_filename = ""

# Quick Sample Loader
col_upload, col_sample = st.columns([3, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF or DOCX)",
        type=["pdf", "docx"],
        help="Upload standard resume documents up to 10MB.",
    )

with col_sample:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    sample_options = ["None", "Anurag Mishra (Real PDF)", "Synthetic Sample 01 (DOCX)", "Synthetic Sample 16 (PDF)"]
    selected_sample = st.selectbox("Or choose a sample resume:", sample_options)

# Handle Sample selection
file_to_process = None
source_name = ""

if uploaded_file is not None:
    # Size check: 10MB limit
    if uploaded_file.size > 10 * 1024 * 1024:
        st.error("File size exceeds 10 MB limit. Please upload a smaller document.")
    else:
        file_to_process = uploaded_file.getvalue()
        source_name = uploaded_file.name
elif selected_sample != "None":
    sample_map = {
        "Anurag Mishra (Real PDF)": "AnuragMishra_resume_2026.pdf",
        "Synthetic Sample 01 (DOCX)": "synthetic_01.docx",
        "Synthetic Sample 16 (PDF)": "synthetic_16.pdf",
    }
    target_rel = sample_map.get(selected_sample)
    target_path = os.path.join(BASE_DIR, "sample_resumes", target_rel)
    if os.path.exists(target_path):
        with open(target_path, "rb") as f:
            file_to_process = f.read()
        source_name = target_rel

# Action Trigger
extract_col, clear_col = st.columns([1, 5])
with extract_col:
    extract_clicked = st.button("🚀 Extract Information", type="primary", disabled=(file_to_process is None))

with clear_col:
    if st.session_state.parsed_data is not None:
        if st.button("Reset / Clear"):
            st.session_state.parsed_data = None
            st.session_state.raw_text = ""
            st.session_state.source_filename = ""
            st.rerun()

# Execution Logic
if extract_clicked and file_to_process is not None:
    with st.spinner("Extracting text and identifying entities..."):
        try:
            # Parse resume through pipeline
            res: ResumeData = parse_resume(file_to_process, source_name)
            # Also get raw document text for display
            doc = extract_document(file_to_process, source_name)

            st.session_state.parsed_data = res
            st.session_state.raw_text = doc.text
            st.session_state.source_filename = source_name
            st.success(f"Successfully processed **{source_name}** in {res.meta.extraction_time_ms} ms!")
        except Exception as e:
            st.error(f"Failed to process document: {str(e)}")

# Display Results
if st.session_state.parsed_data is not None:
    data: ResumeData = st.session_state.parsed_data

    # Display any diagnostic warnings
    if data.meta.warnings:
        for w in data.meta.warnings:
            st.warning(f"⚠️ **Warning**: {w}")

    # Top Overview Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Candidate Name", data.personal.name or "Not Found")
    with m2:
        st.metric("Skills Identified", len(data.skills.all))
    with m3:
        st.metric("Experience Entries", len(data.experience))
    with m4:
        st.metric("Education Entries", len(data.education))
    with m5:
        st.metric("Latency", f"{data.meta.extraction_time_ms} ms")

    st.markdown("---")

    # Download Bar
    st.subheader("📥 Export Structured Data")
    d1, d2, d3 = st.columns(3)
    with d1:
        json_output = export_to_json(data)
        st.download_button(
            label="📄 Download as JSON",
            data=json_output,
            file_name=f"{os.path.splitext(st.session_state.source_filename)[0]}_parsed.json",
            mime="application/json",
            use_container_width=True,
        )

    with d2:
        csv_output = export_candidates_to_csv(data)
        st.download_button(
            label="📊 Download Flattened CSV",
            data=csv_output,
            file_name=f"{os.path.splitext(st.session_state.source_filename)[0]}_candidate.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with d3:
        edu_csv, exp_csv, proj_csv = export_relational_csvs(data)
        combined_relational = f"=== EDUCATION ===\n{edu_csv}\n\n=== EXPERIENCE ===\n{exp_csv}\n\n=== PROJECTS ===\n{proj_csv}"
        st.download_button(
            label="📑 Download Detailed CSVs",
            data=combined_relational,
            file_name=f"{os.path.splitext(st.session_state.source_filename)[0]}_tables.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")

    # Interactive Section Tabs
    tabs = st.tabs(
        [
            "👤 Personal / Contact",
            "📝 Summary",
            "💡 Skills",
            "🎓 Education",
            "💼 Experience",
            "🚀 Projects",
            "🏆 Achievements",
            "📄 Raw Extracted Text",
            "⚙️ Metadata",
        ]
    )

    # 1. Personal & Contact
    with tabs[0]:
        st.subheader("Personal & Contact Information")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Full Name:** {data.personal.name or '—'}")
            st.markdown(f"**Location:** {data.personal.location or '—'}")

            st.markdown("**Email Addresses:**")
            if data.personal.emails:
                for em in data.personal.emails:
                    st.markdown(f"- ✉️ `{em}`")
            else:
                st.write("No email address detected.")

            st.markdown("**Phone Numbers:**")
            if data.personal.phones:
                for ph in data.personal.phones:
                    st.markdown(f"- 📞 `{ph}`")
            else:
                st.write("No phone number detected.")

        with c2:
            st.markdown("**Online Profiles & Links:**")
            links = data.personal.links
            if links.linkedin:
                st.markdown(f"- 🔗 **LinkedIn:** [{links.linkedin}]({links.linkedin})")
            if links.github:
                st.markdown(f"- 🐙 **GitHub:** [{links.github}]({links.github})")
            if links.other:
                for o in links.other:
                    st.markdown(f"- 🌐 [{o}]({o})")
            if not links.linkedin and not links.github and not links.other:
                st.write("No links detected.")

    # 2. Summary
    with tabs[1]:
        st.subheader("Professional Summary / Profile")
        if data.summary:
            st.info(data.summary)
        else:
            st.write("No professional summary section present in this resume.")

    # 3. Skills
    with tabs[2]:
        st.subheader("Skills & Technical Competencies")

        # Grouped view if available
        if data.skills.by_category:
            st.markdown("##### 📂 Skills Grouped by Category")
            for cat, s_list in data.skills.by_category.items():
                st.markdown(f'<div class="category-title">{cat} ({len(s_list)})</div>', unsafe_allow_html=True)
                badges_html = " ".join([f'<span class="badge">{s}</span>' for s in s_list])
                st.markdown(badges_html, unsafe_allow_html=True)
                st.write("")

        st.markdown("##### 🏷️ All Unique Identified Skills")
        if data.skills.all:
            all_badges = " ".join([f'<span class="badge">{s}</span>' for s in data.skills.all])
            st.markdown(all_badges, unsafe_allow_html=True)
        else:
            st.write("No skills identified.")

    # 4. Education
    with tabs[3]:
        st.subheader("Educational Background")
        if data.education:
            for idx, edu in enumerate(data.education):
                with st.container():
                    st.markdown(
                        f"""
                        <div class="edu-card">
                            <h4 style="margin: 0; color: #1e293b;">{edu.degree or 'Degree Not Specified'}</h4>
                            <p style="margin: 2px 0; color: #475569; font-weight: 500;">🏛️ {edu.institution or 'Institution Not Specified'}</p>
                            <p style="margin: 2px 0; color: #64748b; font-size: 0.9rem;">📍 {edu.location or 'Location Not Listed'} | 📅 {edu.start_year or '—'} – {edu.end_year or '—'}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.write("No education entries detected.")

    # 5. Experience
    with tabs[4]:
        st.subheader("Work Experience")
        if data.experience:
            for exp in data.experience:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="exp-card">
                            <h4 style="margin: 0; color: #1e293b;">{exp.title or 'Job Title Not Specified'}</h4>
                            <p style="margin: 2px 0; color: #2563eb; font-weight: 600;">🏢 {exp.organization or 'Organization Not Specified'}</p>
                            <p style="margin: 2px 0; color: #64748b; font-size: 0.9rem;">📅 {exp.start_date or '—'} – {exp.end_date or '—'} | 📍 {exp.location or 'Location Not Listed'}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if exp.description:
                        for bullet in exp.description:
                            st.markdown(f"- {bullet}")
                    st.write("")
        else:
            st.write("No work experience entries detected.")

    # 6. Projects
    with tabs[5]:
        st.subheader("Projects & Technical Work")
        if data.projects:
            for proj in data.projects:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="proj-card">
                            <h4 style="margin: 0; color: #065f46;">🚀 {proj.name or 'Untitled Project'}</h4>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if proj.technologies:
                        tech_badges = " ".join([f'<span class="badge" style="background:#ecfdf5; color:#047857; border-color:#a7f3d0;">{t}</span>' for t in proj.technologies])
                        st.markdown(tech_badges, unsafe_allow_html=True)
                    if proj.description:
                        for bullet in proj.description:
                            st.markdown(f"- {bullet}")
                    st.write("")
        else:
            st.write("No project entries detected.")

    # 7. Achievements
    with tabs[6]:
        st.subheader("Achievements & Certifications")
        if data.achievements:
            for ach in data.achievements:
                st.markdown(f"- 🏆 {ach}")
        else:
            st.write("No achievements or certifications listed.")

    # 8. Raw Extracted Text
    with tabs[7]:
        st.subheader("Raw Extracted Document Text")
        st.caption("Clean text output extracted from document parser before section segmentation.")
        st.text_area("Extracted Text", st.session_state.raw_text, height=450)

    # 9. Metadata & Diagnostics
    with tabs[8]:
        st.subheader("Document Metadata & Diagnostics")
        st.json(data.meta.model_dump())

elif file_to_process is None:
    st.info("👆 Please upload a PDF or DOCX resume document above, or pick a sample resume from the dropdown.")
