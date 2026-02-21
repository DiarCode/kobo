from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def normalize_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def extract_text_from_file(filename: str, content: bytes) -> str:
    ext = normalize_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type")

    if ext in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore").strip()

    if ext == ".pdf":
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    if ext == ".docx":
        document = Document(BytesIO(content))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraphs).strip()

    return ""
