"""Deterministic text extraction for teacher-uploaded assignment sources."""

from dataclasses import dataclass
from io import BytesIO


PDF_MEDIA_TYPES = {"application/pdf"}
IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png"}


@dataclass
class DocumentExtractionError(Exception):
    message: str
    error_code: str


def _clean_text(value):
    lines = [line.strip() for line in str(value or "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _extract_pdf(content):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise DocumentExtractionError(
            "PDF text extraction is not installed",
            "pdf_extractor_unavailable",
        ) from error
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise DocumentExtractionError(
            "The PDF could not be read",
            "pdf_read_failed",
        ) from error
    text = _clean_text(text)
    if not text:
        raise DocumentExtractionError(
            "No embedded text was found; use image OCR instead",
            "pdf_text_empty",
        )
    return text, "pdf_text", []


def _rapidocr_lines(result):
    if hasattr(result, "txts"):
        return list(result.txts or [])
    if isinstance(result, tuple):
        result = result[0]
    lines = []
    for item in result or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lines.append(str(item[1]))
    return lines


def _extract_image(content):
    try:
        from rapidocr import RapidOCR
    except ImportError as error:
        raise DocumentExtractionError(
            "Image OCR is not installed",
            "ocr_unavailable",
        ) from error
    try:
        result = RapidOCR()(content)
        text = _clean_text("\n".join(_rapidocr_lines(result)))
    except Exception as error:
        raise DocumentExtractionError(
            "The image could not be recognized",
            "ocr_failed",
        ) from error
    if not text:
        raise DocumentExtractionError(
            "No readable text was recognized in the image",
            "ocr_text_empty",
        )
    return text, "rapidocr", []


def extract_document_text(content, media_type):
    """Return ``(text, extractor_code, warnings)`` for an allowlisted document."""
    normalized_media_type = str(media_type or "").split(";", 1)[0].lower()
    if normalized_media_type in PDF_MEDIA_TYPES:
        return _extract_pdf(content)
    if normalized_media_type in IMAGE_MEDIA_TYPES:
        return _extract_image(content)
    raise DocumentExtractionError(
        "Only PDF, PNG, and JPEG assignment sources can be recognized",
        "unsupported_document_type",
    )
