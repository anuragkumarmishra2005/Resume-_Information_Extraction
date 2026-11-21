"""Document text and metadata extractor for PDF and DOCX resume files.

Handles multi-page PDFs, tables, bullets, embedded hyperlinks, font heuristics,
and scanned PDF detection.
"""

from dataclasses import dataclass, field
import io
import logging
import os
import re
from typing import BinaryIO, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    """Container for extracted document text, metadata, and diagnostic warnings."""
    text: str
    pages: int
    links: List[str] = field(default_factory=list)
    top_large_text: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source_file: str = ""


def normalize_text(text: str) -> str:
    """Normalize whitespace, bullets, unicode dashes, and punctuation.

    Args:
        text: Raw extracted text string.

    Returns:
        Cleaned and normalized text.
    """
    if not text:
        return ""

    # Replace non-breaking spaces and exotic whitespace
    text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Standardize unicode dashes and hyphens
    text = re.sub(r"[\u2012\u2013\u2014\u2015\u2212]", "-", text)

    # Standardize quotes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    # Standardize bullet characters at start of lines or phrases
    text = re.sub(r"^[\s]*[\u2022\u25cf\u25cb\u25aa\u25ab\u2023\u2043\u2219\*\-]\s*", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"(?<=\n)[\s]*[\u2022\u25cf\u25cb\u25aa\u25ab\u2023\u2043\u2219\*\-]\s*", "• ", text)

    # Fix multiple blank lines
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: List[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _extract_pdf(file_input: Union[str, bytes, BinaryIO], filename: str) -> ExtractedDocument:
    """Extract text, links, font metadata, and page count from a PDF file."""
    pages_count = 0
    extracted_text_chunks: List[str] = []
    extracted_links: List[str] = []
    top_large_text: List[str] = []
    warnings: List[str] = []
    has_images = False

    # Check for empty file
    if isinstance(file_input, bytes) and len(file_input) == 0:
        return ExtractedDocument(
            text="", pages=0, warnings=["The provided PDF file is empty (0 bytes)."], source_file=filename
        )
    if isinstance(file_input, str) and (not os.path.exists(file_input) or os.path.getsize(file_input) == 0):
        return ExtractedDocument(
            text="", pages=0, warnings=["The provided PDF file is empty or missing."], source_file=filename
        )

    # 1. Try PyMuPDF (fitz) first as it gives superior layout and span typography
    try:
        import fitz

        doc = (
            fitz.open(stream=file_input, filetype="pdf")
            if isinstance(file_input, bytes)
            else fitz.open(file_input)
        )
        pages_count = len(doc)
        max_font_size = 0.0

        for idx, page in enumerate(doc):
            extracted_text_chunks.append(page.get_text())
            for link in page.get_links():
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://", "mailto:")):
                    extracted_links.append(uri)
            if len(page.get_images()) > 0:
                has_images = True

            # Analyze fonts on page 1 for candidate name heuristic
            if idx == 0:
                page_dict = page.get_text("dict")
                for block in page_dict.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                s_text = span.get("text", "").strip()
                                s_size = span.get("size", 0.0)
                                if s_text and s_size > max_font_size:
                                    max_font_size = s_size

                # Now collect text spans with near-maximum font size (> max - 1.0)
                if max_font_size > 11.0:
                    for block in page_dict.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                span_texts = []
                                for span in line.get("spans", []):
                                    if span.get("size", 0.0) >= (max_font_size - 1.0):
                                        span_texts.append(span.get("text", "").strip())
                                line_large_text = " ".join(t for t in span_texts if t).strip()
                                if line_large_text and len(line_large_text) < 100:
                                    top_large_text.append(line_large_text)

        doc.close()

    except Exception as e:
        logger.warning("PyMuPDF extraction failed: %s, falling back to pdfplumber", e)
        try:
            import pdfplumber

            pdf_obj = (
                pdfplumber.open(io.BytesIO(file_input))
                if isinstance(file_input, bytes)
                else pdfplumber.open(file_input)
            )
            with pdf_obj as pdf:
                pages_count = len(pdf.pages)
                for idx, page in enumerate(pdf.pages):
                    p_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    extracted_text_chunks.append(p_text)
                    if getattr(page, "images", None) and len(page.images) > 0:
                        has_images = True
                    for h in getattr(page, "hyperlinks", []):
                        uri = h.get("uri")
                        if uri and uri.startswith(("http://", "https://", "mailto:")):
                            extracted_links.append(uri)
        except Exception as e2:
            logger.error("All PDF extractors failed on %s: %s", filename, e2)
            return ExtractedDocument(
                text="",
                pages=0,
                warnings=[f"Failed to read PDF document: corrupted or invalid format ({str(e2)})"],
                source_file=filename,
            )

    combined_text = normalize_text("\n\n".join(extracted_text_chunks))

    # Detect scanned or image-only document
    clean_char_count = len(re.sub(r"\s+", "", combined_text))
    if clean_char_count < 50:
        if has_images or pages_count > 0:
            warnings.append(
                "Document appears to be scanned or image-only. Text extraction may be incomplete or empty."
            )
        else:
            warnings.append("Document contains little or no extractable text.")

    # Deduplicate links
    unique_links: List[str] = []
    for link in extracted_links:
        if link not in unique_links:
            unique_links.append(link)

    return ExtractedDocument(
        text=combined_text,
        pages=max(pages_count, 1),
        links=unique_links,
        top_large_text=top_large_text,
        warnings=warnings,
        source_file=filename,
    )


def _extract_docx(file_input: Union[str, bytes, BinaryIO], filename: str) -> ExtractedDocument:
    """Extract text, tables, and hyperlinks from a DOCX file."""
    try:
        import docx
        from docx.oxml.ns import qn

        stream = io.BytesIO(file_input) if isinstance(file_input, bytes) else file_input
        doc = docx.Document(stream)

        text_lines: List[str] = []
        links: List[str] = []
        warnings: List[str] = []

        # Extract relationships for hyperlinks
        rels = {}
        for r_id, rel in doc.part.rels.items():
            if "hyperlink" in rel.reltype:
                rels[r_id] = rel.target_ref

        # Extract paragraphs
        for p in doc.paragraphs:
            p_text = p.text.strip()
            # Also check XML for inline hyperlinks
            for elem in p._p.xpath(".//w:hyperlink"):
                r_id = elem.get(qn("r:id"))
                if r_id in rels:
                    target = rels[r_id]
                    if target.startswith(("http://", "https://", "mailto:")):
                        links.append(target)
            if p_text:
                text_lines.append(p_text)

        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    # Remove adjacent identical cells caused by merging
                    deduped_cells: List[str] = []
                    for c in row_cells:
                        if not deduped_cells or deduped_cells[-1] != c:
                            deduped_cells.append(c)
                    text_lines.append(" | ".join(deduped_cells))

        combined_text = normalize_text("\n".join(text_lines))
        if len(combined_text.strip()) == 0:
            warnings.append("DOCX document is empty or contains no extractable text.")

        # Estimate page count (standard ~500 words per page in DOCX)
        word_count = len(combined_text.split())
        estimated_pages = max(1, (word_count + 499) // 500)

        # Deduplicate links
        unique_links: List[str] = []
        for lk in links:
            if lk not in unique_links:
                unique_links.append(lk)

        return ExtractedDocument(
            text=combined_text,
            pages=estimated_pages,
            links=unique_links,
            warnings=warnings,
            source_file=filename,
        )

    except Exception as e:
        logger.error("DOCX extraction failed for %s: %s", filename, e)
        return ExtractedDocument(
            text="",
            pages=0,
            warnings=[f"Failed to read DOCX document: {str(e)}"],
            source_file=filename,
        )


def extract_document(file_input: Union[str, bytes, BinaryIO], filename: str) -> ExtractedDocument:
    """Extract clean text and metadata from PDF or DOCX resume document.

    Args:
        file_input: File path, bytes, or file-like object.
        filename: Original file name.

    Returns:
        ExtractedDocument instance containing text, pages, links, and warnings.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return _extract_pdf(file_input, filename)
    elif lower_name.endswith((".docx", ".doc")):
        return _extract_docx(file_input, filename)
    else:
        return ExtractedDocument(
            text="",
            pages=0,
            warnings=[f"Unsupported file format '{filename}'. Please upload a PDF or DOCX document."],
            source_file=filename,
        )
