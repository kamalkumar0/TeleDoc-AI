"""Gemini embeddings wrapper.

Uses ``text-embedding-004``. Document chunks and queries use *different* task
types (``RETRIEVAL_DOCUMENT`` vs ``RETRIEVAL_QUERY``); this asymmetry is
recommended by Google and measurably improves retrieval quality, so it is kept
explicit here.
"""

import logging
import time

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# google-generativeai expects the model name prefixed with "models/".
_MODEL_NAME = f"models/{EMBEDDING_MODEL}"

_MAX_RETRIES = 3

# Quota errors (HTTP 429) are throttled per minute on the free tier, so we wait
# long enough for the rate-limit window to reset rather than backing off briefly.
_QUOTA_RETRY_DELAY_SECONDS = 35.0

# The embedding API counts each chunk as one request, so document chunks are
# embedded in sub-batches of this size rather than all at once.
_EMBED_BATCH_SIZE = 50


def _embed_with_backoff(content, task_type: str):
    """Call ``embed_content`` with exponential backoff on rate-limit errors.

    Args:
        content: A single string or a list of strings.
        task_type: Either ``RETRIEVAL_DOCUMENT`` or ``RETRIEVAL_QUERY``.

    Returns:
        The raw embedding payload (a list[float] or list[list[float]]).

    Raises:
        Exception: re-raises the last error if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=_MODEL_NAME,
                content=content,
                task_type=task_type,
            )
            return result["embedding"]
        except google_exceptions.ResourceExhausted as exc:
            # 429 / quota errors are throttled per minute; wait for the window
            # to reset before retrying.
            last_exc = exc
            logger.warning(
                "Embedding rate-limited (attempt %d/%d); retrying in %.0fs",
                attempt + 1,
                _MAX_RETRIES,
                _QUOTA_RETRY_DELAY_SECONDS,
            )
            time.sleep(_QUOTA_RETRY_DELAY_SECONDS)
        except Exception as exc:  # non-retryable: log and surface immediately
            logger.error("Embedding call failed: %s", exc)
            raise

    logger.error("Embedding still failing after %d retries.", _MAX_RETRIES)
    assert last_exc is not None
    raise last_exc


def embed_text(text: str) -> list[float]:
    """Embed a single query string.

    Args:
        text: The user's question.

    Returns:
        The embedding vector.
    """
    return _embed_with_backoff(text, task_type="RETRIEVAL_QUERY")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed document chunks, splitting into sub-batches to respect API limits.

    Args:
        texts: The chunk strings to embed.

    Returns:
        One embedding vector per input chunk, in order. Empty list for empty input.
    """
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH_SIZE):
        sub_batch = texts[start : start + _EMBED_BATCH_SIZE]
        logger.info(
            "Embedding chunks %d-%d of %d",
            start + 1,
            start + len(sub_batch),
            len(texts),
        )
        vectors.extend(
            _embed_with_backoff(sub_batch, task_type="RETRIEVAL_DOCUMENT")
        )
    return vectors
