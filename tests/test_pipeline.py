"""Unit tests for pipeline resilience, bad input, corrupted files, and scanned PDFs."""

import io
from resume_parser.pipeline import parse_resume
from resume_parser.extractors.text_extractor import extract_document


def test_empty_bytes_handling():
    # Empty file must return graceful result with warning and never crash
    resume = parse_resume(b"", "empty_resume.pdf")
    assert resume.personal.name is None
    assert resume.personal.emails == []
    assert len(resume.meta.warnings) >= 1
    assert any("empty" in w.lower() for w in resume.meta.warnings)


def test_corrupted_file_handling():
    # Corrupted binary data
    garbage_data = b"This is random garbage that is not a valid PDF or DOCX file"
    resume = parse_resume(garbage_data, "broken.pdf")
    assert resume.personal.name is None
    assert len(resume.meta.warnings) >= 1
    assert any("corrupted" in w.lower() or "failed" in w.lower() for w in resume.meta.warnings)


def test_unsupported_file_extension():
    # Unsupported file extension
    resume = parse_resume(b"hello world", "document.txt")
    assert len(resume.meta.warnings) >= 1
    assert any("unsupported" in w.lower() for w in resume.meta.warnings)


def test_scanned_pdf_warning():
    # Create an image-only dummy PDF using reportlab or synthetic minimal PDF with only image
    from reportlab.pdfgen import canvas
    from PIL import Image

    # Create dummy 100x100 white image
    img = Image.new("RGB", (100, 100), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Make PDF with image only and no text
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    from reportlab.lib.utils import ImageReader

    c.drawImage(ImageReader(img_byte_arr), 100, 100, width=200, height=200)
    c.showPage()
    c.save()

    pdf_bytes = pdf_buf.getvalue()
    doc = extract_document(pdf_bytes, "scanned.pdf")
    assert any("scanned" in w.lower() or "image-only" in w.lower() or "little or no" in w.lower() for w in doc.warnings)
