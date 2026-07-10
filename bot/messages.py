"""All user-facing strings in one place.

Keeping copy out of the handlers makes tone changes and future localization a
single-file edit. Strings with ``{placeholders}`` are formatted at call time.
"""

# Rendered with parse_mode="HTML". HTML mode (unlike legacy Markdown) does not
# treat underscores as formatting, so command names like /clear_memory are safe.
# Literal &, < and > must be HTML-escaped.
WELCOME_MESSAGE = (
    "👋 <b>Welcome to the PDF Q&amp;A bot!</b>\n\n"
    "I answer questions using <b>only</b> the PDFs you upload — no outside "
    "knowledge, no guessing.\n\n"
    "<b>How to use me:</b>\n"
    "1️⃣ Upload a PDF (just send the file).\n"
    "2️⃣ Ask a question — either type it directly or use "
    "<code>/ask &lt;question&gt;</code>.\n\n"
    "<b>Examples:</b>\n"
    "• <i>What does section 3 say about refunds?</i>\n"
    "• <code>/ask Who is the author?</code>\n\n"
    "<b>Commands:</b>\n"
    "/start, /help — show this message\n"
    "/ask &lt;question&gt; — ask about your documents\n"
    "/list — list your uploaded PDFs\n"
    "/clear — delete all your documents and memory\n"
    "/clear_memory — forget our conversation, keep documents\n\n"
    "Max file size: 20 MB. PDFs only."
)

PDF_RECEIVED = "📄 Processing {filename} ({size_mb:.1f} MB)..."

PDF_PROCESSED = (
    "✅ Done. {filename} indexed into {chunk_count} chunks. "
    "Ask me anything about it."
)

PDF_TOO_LARGE = "❌ That file is {size_mb:.1f} MB. Maximum is 20 MB."

NOT_A_PDF = "❌ I only accept PDF files."

PDF_EMPTY = (
    "❌ I couldn't extract any text from that PDF. "
    "It may be scanned images rather than text."
)

NO_DOCUMENTS_YET = (
    "You haven't uploaded any documents yet. Send me a PDF first."
)

NO_RELEVANT_CONTEXT = (
    "I couldn't find anything relevant in your uploaded documents. "
    "Try rephrasing, or upload a relevant document."
)

# Rendered with parse_mode="HTML".
EMPTY_QUESTION = (
    "Please include a question, e.g. "
    "<code>/ask What is this document about?</code>"
)

MEMORY_CLEARED = "🧠 Conversation memory cleared. Your documents are still here."

ALL_CLEARED = "🗑️ Cleared everything — all your documents and conversation memory are gone."

LIST_HEADER = "📚 Your uploaded documents:"

GENERIC_ERROR = "⚠️ Something went wrong on my end. Please try again."
