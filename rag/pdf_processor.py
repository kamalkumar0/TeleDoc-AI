"""PDF text extraction and chunking.

Two pure functions, no shared state. Telegram hands us the file as bytes, so
extraction works from an in-memory buffer rather than a filesystem path.
"""

import logging
import re

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Map common "smart" punctuation to plain ASCII equivalents.
_PUNCTUATION_REPLACEMENTS = {
    "‘": "'",  # left single quote
    "’": "'",  # right single quote
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "–": "-",  # en dash
    "—": "-",  # em dash
    "…": "...",  # ellipsis
}


def _clean(text: str) -> str:
    """Normalise extracted text: ASCII punctuation, single spaces, no blank lines."""
    for smart, plain in _PUNCTUATION_REPLACEMENTS.items():
        text = text.replace(smart, plain)

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        # Collapse runs of whitespace within the line to a single space.
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_text(pdf_bytes: bytes) -> str:
    """Extract and clean all text from a PDF supplied as raw bytes.

    Args:
        pdf_bytes: The PDF file contents.

    Returns:
        A single cleaned string containing the text of every page.

    Raises:
        ValueError: if the bytes cannot be opened as a PDF.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises a variety of errors for bad input
        logger.error("Failed to open PDF from bytes: %s", exc)
        raise ValueError("Could not read the uploaded file as a PDF.") from exc

    pages: list[str] = []
    try:
        for page in doc:
            pages.append(page.get_text())
    finally:
        doc.close()

    return _clean("\n".join(pages))


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping fixed-size chunks using a sliding window.

    Args:
        text: The source text.
        chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks.

    Returns:
        A list of chunk strings. Empty list if ``text`` is empty/whitespace.

    Raises:
        ValueError: if ``chunk_size <= overlap`` (the window would not advance).
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap.")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        # Stop once the window has consumed the whole string.
        if start + chunk_size >= len(text):
            break
    return chunks
