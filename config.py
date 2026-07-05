"""Central configuration: loads environment variables and defines constants.

All tunable values live here so nothing is hardcoded elsewhere in the codebase.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()

# --- Secrets (from environment) -------------------------------------------------

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# --- RAG / chunking constants ---------------------------------------------------

CHUNK_SIZE: int = 500          # characters per chunk
CHUNK_OVERLAP: int = 50        # overlapping characters between consecutive chunks
MAX_PDF_SIZE_MB: int = 20      # reject uploads larger than this
TOP_K_CHUNKS: int = 5          # how many chunks to retrieve per question
MEMORY_LAST_N: int = 5         # conversation exchanges kept per user
# Drop retrieved chunks whose cosine similarity is below this. Calibrated for
# gemini-embedding-001, whose similarity scores run lower than text-embedding-004
# (relevant matches commonly land in the 0.25-0.45 range). The LLM prompt is the
# primary grounding guard; this threshold is just a coarse pre-filter.
SIMILARITY_THRESHOLD: float = 0.2

# --- Model identifiers ----------------------------------------------------------

# Model names valid for the current Gemini API (the older gemini-1.5-flash /
# text-embedding-004 are not available on newer API keys/endpoints).
GEMINI_MODEL: str = "gemini-2.5-flash"
EMBEDDING_MODEL: str = "gemini-embedding-001"

# --- Storage --------------------------------------------------------------------

CHROMA_PATH: str = str(Path(os.getenv("CHROMA_PATH", "./chroma_db")))


def validate_config() -> None:
    """Raise a clear error at startup if required secrets are missing.

    Raises:
        RuntimeError: if either API key / token is not set.
    """
    missing: list[str] = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your keys."
        )
