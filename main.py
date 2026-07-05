"""Entrypoint: wire handlers into the Telegram application and start polling."""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import handlers
from config import TELEGRAM_BOT_TOKEN, validate_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Construct the Telegram Application with all handlers registered.

    Returns:
        A configured, ready-to-run ``Application``.
    """
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands first.
    app.add_handler(CommandHandler(["start", "help"], handlers.start_handler))
    app.add_handler(CommandHandler("ask", handlers.ask_handler))
    app.add_handler(CommandHandler("list", handlers.list_handler))
    app.add_handler(CommandHandler("clear", handlers.clear_handler))
    app.add_handler(CommandHandler("clear_memory", handlers.clear_memory_handler))

    # Document uploads (PDFs arrive as documents).
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.document_handler))

    # Any remaining non-command text is treated as a question.
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_handler)
    )

    # Final safety net.
    app.add_error_handler(handlers.error_handler)
    return app


def main() -> None:
    """Validate configuration and run the bot until interrupted."""
    validate_config()
    app = build_application()
    logger.info("Starting Telegram PDF RAG bot…")
    app.run_polling()


if __name__ == "__main__":
    main()
