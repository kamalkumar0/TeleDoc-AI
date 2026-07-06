"""Gemini answer generation for the RAG pipeline.

Builds a strictly document-grounded prompt and streams the model's response.
The system prompt forbids the model from using outside knowledge: if the
retrieved context does not contain the answer, it must say so verbatim.
"""

import logging
from collections.abc import AsyncIterator

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Configure the SDK once at import time.
genai.configure(api_key=GEMINI_API_KEY)

_model = genai.GenerativeModel(GEMINI_MODEL)

# The exact fallback string the model must emit when context is insufficient.
GROUNDING_FALLBACK = "I couldn't find that information in your uploaded documents."

_PROMPT_TEMPLATE = """You are a strict document-grounded assistant. You answer questions ONLY using the
information in the CONTEXT section below. If the CONTEXT does not contain the answer,
respond exactly: "{fallback}"

Do not use outside knowledge. Do not make assumptions. Do not speculate.

CONVERSATION HISTORY (for follow-up context only — not source material):
{history}

CONTEXT (the only source you may use):
{context}

QUESTION: {question}

ANSWER:"""


def _format_history(history: list[tuple[str, str]]) -> str:
    """Render prior Q/A pairs, or a placeholder if there are none."""
    if not history:
        return "(none)"
    lines: list[str] = []
    for question, answer in history:
        lines.append(f"Q: {question}")
        lines.append(f"A: {answer}")
    return "\n".join(lines)


def _format_context(context_chunks: list[str]) -> str:
    """Render retrieved chunks as a numbered list."""
    if not context_chunks:
        return "(no context retrieved)"
    return "\n".join(f"[{i + 1}] {chunk}" for i, chunk in enumerate(context_chunks))


def _build_prompt(
    question: str, context_chunks: list[str], history: list[tuple[str, str]]
) -> str:
    """Assemble the full prompt from its parts."""
    return _PROMPT_TEMPLATE.format(
        fallback=GROUNDING_FALLBACK,
        history=_format_history(history),
        context=_format_context(context_chunks),
        question=question,
    )


async def generate_answer(
    question: str,
    context_chunks: list[str],
    history: list[tuple[str, str]],
) -> AsyncIterator[str]:
    """Stream a grounded answer for a question given retrieved context.

    Args:
        question: The user's question.
        context_chunks: Retrieved chunk texts (the only allowed source).
        history: Recent (question, answer) pairs for follow-up continuity.

    Yields:
        Incremental text fragments of the model's answer.
    """
    prompt = _build_prompt(question, context_chunks, history)
    try:
        response = await _model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            # Some streamed chunks (e.g. safety-only frames) carry no text.
            if getattr(chunk, "text", None):
                yield chunk.text
    except Exception as exc:
        logger.error("Gemini generation failed: %s", exc)
        # Surface a safe fallback rather than crashing the handler.
        yield "Sorry, I ran into an error while generating an answer. Please try again."
