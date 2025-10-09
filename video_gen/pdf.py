from __future__ import annotations

import os
from typing import Optional


def extract_text_from_pdf(pdf_path: str, max_megabytes: int = 60) -> str:
    """
    Extract text from a PDF using pdfplumber with a PyPDF2 fallback.

    Enforces a maximum file size in megabytes.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    file_size_bytes = os.path.getsize(pdf_path)
    max_bytes = max_megabytes * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"PDF size {file_size_bytes/1024/1024:.2f}MB exceeds limit of {max_megabytes}MB"
        )

    # Try pdfplumber first
    try:
        import pdfplumber  # type: ignore

        text_chunks: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
        text = "\n\n".join(chunk.strip() for chunk in text_chunks if chunk and chunk.strip())
        if text.strip():
            return text
    except Exception:
        # Fall back to PyPDF2 below
        pass

    # Fallback: PyPDF2
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(pdf_path)
        pages_text: list[str] = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n\n".join(s.strip() for s in pages_text if s and s.strip())
        return text
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to extract text from PDF: {exc}") from exc
