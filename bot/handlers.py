"""Telegram command and message handlers.

Each handler is async. Heavy/blocking work (PDF extraction, embedding, Chroma
writes) is pushed off the event loop with ``asyncio.to_thread``. All API calls
are wrapped in try/except and logged; the registered ``error_handler`` is the
final safety net so an unhandled exception never crashes the bot.
"""

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes

from bot import messages
from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MAX_PDF_SIZE_MB,
    TOP_K_CHUNKS,
)
from memory import conversation_memory
from rag import embeddings, generator, pdf_processor, vector_store

logger = logging.getLogger(__name__)

_MAX_PDF_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024

# Re-edit the streamed reply once this many new characters have accumulated.
_STREAM_EDIT_EVERY_CHARS = 80

# Telegram rejects messages longer than 4096 characters; truncate to fit.
_TELEGRAM_MAX_CHARS = 4096


# --- Command handlers -----------------------------------------------------------


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start and /help: send the welcome / usage message."""
    await update.effective_message.reply_text(
        messages.WELCOME_MESSAGE, parse_mode="HTML"
    )


async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list: show the user's uploaded PDF filenames."""
    user_id = update.effective_user.id
    docs = await asyncio.to_thread(vector_store.list_documents, user_id)
    if not docs:
        await update.effective_message.reply_text(messages.NO_DOCUMENTS_YET)
        return
    body = "\n".join(f"• {name}" for name in docs)
    await update.effective_message.reply_text(f"{messages.LIST_HEADER}\n{body}")


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear: delete all of the user's documents and conversation memory."""
    user_id = update.effective_user.id
    await asyncio.to_thread(vector_store.clear_user, user_id)
    conversation_memory.clear(user_id)
    await update.effective_message.reply_text(messages.ALL_CLEARED)


async def clear_memory_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /clear_memory: forget conversation history but keep documents."""
    conversation_memory.clear(update.effective_user.id)
    await update.effective_message.reply_text(messages.MEMORY_CLEARED)


async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask <question>: route the argument text through the RAG pipeline."""
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.effective_message.reply_text(
            messages.EMPTY_QUESTION, parse_mode="HTML"
        )
        return
    await _answer_question(update, question)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a plain text message: treat the whole message as a question."""
    question = (update.effective_message.text or "").strip()
    if not question:
        return
    await _answer_question(update, question)


# --- Document upload ------------------------------------------------------------


async def document_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle an uploaded document: validate, extract, chunk, embed, and store."""
    user_id = update.effective_user.id
    document = update.effective_message.document

    filename = document.file_name or "document.pdf"
    is_pdf = (document.mime_type == "application/pdf") or filename.lower().endswith(
        ".pdf"
    )
    if not is_pdf:
        await update.effective_message.reply_text(messages.NOT_A_PDF)
        return

    size_bytes = document.file_size or 0
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes > _MAX_PDF_BYTES:
        await update.effective_message.reply_text(
            messages.PDF_TOO_LARGE.format(size_mb=size_mb)
        )
        return

    await update.effective_message.reply_text(
        messages.PDF_RECEIVED.format(filename=filename, size_mb=size_mb)
    )
    await update.effective_chat.send_chat_action(ChatAction.TYPING)

    try:
        tg_file = await document.get_file()
        pdf_bytes = bytes(await tg_file.download_as_bytearray())

        # Extraction, chunking and embedding are blocking; keep them off the loop.
        chunk_count = await asyncio.to_thread(
            _ingest_pdf, user_id, filename, pdf_bytes
        )
    except ValueError:
        # Raised by the PDF processor for unreadable files.
        await update.effective_message.reply_text(messages.NOT_A_PDF)
        return
    except Exception as exc:
        logger.error("Failed to process PDF for user %s: %s", user_id, exc)
        await update.effective_message.reply_text(messages.GENERIC_ERROR)
        return

    if chunk_count == 0:
        await update.effective_message.reply_text(messages.PDF_EMPTY)
        return

    await update.effective_message.reply_text(
        messages.PDF_PROCESSED.format(filename=filename, chunk_count=chunk_count)
    )


def _ingest_pdf(user_id: int, filename: str, pdf_bytes: bytes) -> int:
    """Extract, chunk, embed, and store a PDF. Runs in a worker thread.

    Args:
        user_id: Telegram user id.
        filename: Original filename (used as metadata/source).
        pdf_bytes: Raw PDF contents.

    Returns:
        The number of chunks stored (0 if the PDF held no extractable text).
    """
    text = pdf_processor.extract_text(pdf_bytes)
    chunks = pdf_processor.chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks:
        return 0
    vectors = embeddings.embed_batch(chunks)
    vector_store.add_document(user_id, filename, chunks, vectors)
    return len(chunks)


# --- RAG question answering -----------------------------------------------------


async def _answer_question(update: Update, question: str) -> None:
    """Run the full RAG pipeline for a question and stream the answer back."""
    user_id = update.effective_user.id
    chat = update.effective_chat

    # Fast guard: no documents at all.
    docs = await asyncio.to_thread(vector_store.list_documents, user_id)
    if not docs:
        await update.effective_message.reply_text(messages.NO_DOCUMENTS_YET)
        return

    await chat.send_chat_action(ChatAction.TYPING)

    # Embed the query and retrieve relevant chunks (blocking I/O -> thread).
    try:
        query_vector = await asyncio.to_thread(embeddings.embed_text, question)
        matches = await asyncio.to_thread(
            vector_store.query, user_id, query_vector, TOP_K_CHUNKS
        )
    except Exception as exc:
        logger.error("Retrieval failed for user %s: %s", user_id, exc)
        await update.effective_message.reply_text(messages.GENERIC_ERROR)
        return

    if not matches:
        await update.effective_message.reply_text(messages.NO_RELEVANT_CONTEXT)
        return

    context_chunks = [m["text"] for m in matches]
    history = conversation_memory.get_history(user_id)

    answer = await _stream_answer(update, question, context_chunks, history)
    if answer:
        conversation_memory.add_exchange(user_id, question, answer)


async def _stream_answer(
    update: Update,
    question: str,
    context_chunks: list[str],
    history: list[tuple[str, str]],
) -> str:
    """Stream Gemini's answer into a single Telegram message, editing as it grows.

    Returns:
        The full answer text (empty string if nothing was produced).
    """
    chat = update.effective_chat
    sent = await update.effective_message.reply_text("…")  # placeholder we keep editing

    accumulated = ""
    last_rendered_len = 0
    try:
        async for fragment in generator.generate_answer(
            question, context_chunks, history
        ):
            accumulated += fragment
            # Throttle edits: only re-render after enough new text accumulates.
            if len(accumulated) - last_rendered_len >= _STREAM_EDIT_EVERY_CHARS:
                await _safe_edit(sent, accumulated)
                last_rendered_len = len(accumulated)
                await chat.send_chat_action(ChatAction.TYPING)
    except Exception as exc:
        logger.error("Streaming answer failed: %s", exc)

    # Final render with the complete text.
    final = accumulated.strip() or messages.GENERIC_ERROR
    await _safe_edit(sent, final)
    return accumulated.strip()


async def _safe_edit(message, text: str) -> None:
    """Edit a message, tolerating Telegram's rate limits and no-op edits."""
    if len(text) > _TELEGRAM_MAX_CHARS:
        text = text[: _TELEGRAM_MAX_CHARS - 1] + "…"
    try:
        await message.edit_text(text)
    except RetryAfter as exc:
        # Respect the server-requested cooldown, then try once more.
        await asyncio.sleep(exc.retry_after)
        try:
            await message.edit_text(text)
        except BadRequest:
            pass
    except BadRequest:
        # "Message is not modified" or similar — safe to ignore.
        pass


# --- Global error handler -------------------------------------------------------


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all: log the exception and send a generic message to the user."""
    logger.error("Unhandled exception while processing update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(messages.GENERIC_ERROR)
        except Exception:
            # Never let the error handler itself raise.
            logger.error("Failed to notify user of error", exc_info=True)
