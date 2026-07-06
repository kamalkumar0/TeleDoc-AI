# Setup Guide — Telegram PDF RAG Bot

This guide takes you from a **completely fresh computer** to a **running Telegram
bot** that can read your PDFs and answer questions about them. No prior experience
assumed — every step is spelled out for Windows, macOS, and Linux.

If you get stuck, jump to [Troubleshooting](#9-troubleshooting) at the bottom — it
covers the exact problems that come up most often.

---

## 0. What you're building and what you'll need

This is a **Telegram bot**. You run a small Python program on your computer; it
connects to Telegram and to Google's Gemini AI. You then chat with your bot inside
the normal Telegram app — upload a PDF, ask questions, get answers grounded in that
PDF.

You will need to create two free accounts/keys along the way:

1. A **Telegram bot token** (free, from Telegram's "BotFather").
2. A **Google Gemini API key** (free tier available, from Google AI Studio).

Total time: ~20–30 minutes the first time.

> **A few words you'll see a lot:**
> - **Terminal** — the text window where you type commands. On Windows it's
>   **PowerShell**; on macOS it's **Terminal**; on Linux it's your shell. Open it
>   and you get a prompt where you type the commands in the grey boxes below.
> - **Python** — the programming language this bot is written in.
> - **Virtual environment (venv)** — a private folder that holds this project's
>   Python packages, so they don't clash with anything else on your machine.
> - **API key / token** — a secret password that lets the program talk to a service
>   (Telegram, Gemini). Treat them like passwords; never share or commit them.

---

## 1. Install the prerequisites

You need **Python** (version **3.11 or 3.12**) and, to download the project,
**Git** (optional — you can also download a ZIP).

> ⚠️ **Use Python 3.11 or 3.12 — not 3.13 or 3.14.**
> This bot uses a package called `chromadb`. On **Windows**, `chromadb`'s helper
> library only has ready-made installers ("wheels") up to Python 3.12. On 3.13/3.14
> it tries to *compile from source* and fails unless you've installed Microsoft's
> C++ build tools. Save yourself the pain: install **Python 3.11**. (macOS/Linux are
> more forgiving, but 3.11/3.12 is still the safe choice.)

### 1.1 Install Python

**Windows**
1. Go to <https://www.python.org/downloads/release/python-3119/> (Python 3.11).
2. Scroll to "Files", download **"Windows installer (64-bit)"**, and run it.
3. **Important:** on the first screen, tick **"Add python.exe to PATH"**, then click
   "Install Now".
4. Close and reopen PowerShell, then verify:
   ```powershell
   py -3.11 --version
   ```
   You should see `Python 3.11.x`.

**macOS**
- Easiest: download the macOS installer from
  <https://www.python.org/downloads/release/python-3119/> and run it. Then:
  ```bash
  python3.11 --version
  ```
- Or, if you use [Homebrew](https://brew.sh):
  ```bash
  brew install python@3.11
  python3.11 --version
  ```

**Linux (Debian/Ubuntu)**
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```
(On Fedora: `sudo dnf install python3.11`.)

### 1.2 Install Git (optional, for cloning)

You only need this if you're getting the project from a Git repository. If you
already have the `telegram_pdf_rag` folder on your machine, skip this.

- **Windows:** download from <https://git-scm.com/download/win> and run the installer
  (defaults are fine).
- **macOS:** `brew install git` — or just run `git --version` and macOS will offer to
  install it.
- **Linux:** `sudo apt install -y git`

Verify anywhere:
```bash
git --version
```

---

## 2. Get the project onto your computer

You most likely received this project as a **zip file** (`telegram_pdf_rag.zip`).
**Unzip it first:**

- **Windows:** right-click `telegram_pdf_rag.zip` → **Extract All…** → **Extract**.
  This creates a `telegram_pdf_rag` folder.
- **macOS:** double-click the zip in Finder; it extracts into a `telegram_pdf_rag`
  folder beside it.
- **Linux:** `unzip telegram_pdf_rag.zip` (install unzip first if needed:
  `sudo apt install -y unzip`).

> *Alternatively, if you were given a **Git URL** instead of a zip:*
> ```bash
> git clone <your-repo-url>
> ```

Now open a terminal **inside** the extracted `telegram_pdf_rag` folder:
- **Windows:** open the folder in File Explorer, type `powershell` in the address bar,
  and press Enter.
- **macOS/Linux:** `cd /path/to/telegram_pdf_rag`

You're in the right place if you can see `main.py` and `requirements.txt`:
```bash
# Windows
dir
# macOS / Linux
ls
```

> **Note:** the zip intentionally does **not** include a virtual environment
> (`.venv`), API keys (`.env`), or cached data — you create those yourself in the
> steps below. That's normal and expected.

---

## 3. Get your API keys

You need **two** keys. Get them now; you'll paste them into a file in Step 5.

### 3.1 Telegram bot token (from BotFather)

1. Open Telegram (phone or desktop). In the search bar, find **@BotFather** (it has a
   blue verified checkmark).
2. Start a chat and send: `/newbot`
3. BotFather asks for:
   - a **name** for your bot (any display name, e.g. `My PDF Bot`), then
   - a **username** that must end in `bot` (e.g. `my_pdf_rag_bot`).
4. BotFather replies with a line like:
   ```
   Use this token to access the HTTP API:
   8123456789:AAH....your-long-token....xyz
   ```
   **Copy that whole token.** That's your `TELEGRAM_BOT_TOKEN`.
5. Keep this chat — your bot is reachable at `https://t.me/<your_bot_username>`.

### 3.2 Google Gemini API key (from AI Studio)

1. Go to <https://aistudio.google.com/apikey> and sign in with a Google account.
2. Click **"Create API key"** (you can create it in a new project).
3. Copy the key. That's your `GEMINI_API_KEY`.

> The free tier is enough to try the bot. It has daily/per-minute limits — see
> [Section 10](#10-notes-models-and-free-tier-limits).

---

## 4. Create the environment and install dependencies

Make sure your terminal is **inside the `telegram_pdf_rag` folder** (Step 2).

### 4.1 Create the virtual environment

**Windows (PowerShell):**
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```
> If activation gives a red "running scripts is disabled" error, run this once, then
> re-run the activate line:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

**macOS / Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

After activating, your prompt shows `(.venv)` at the start. That means the venv is
active. (To leave it later, type `deactivate`.)

### 4.2 Install the dependencies

```bash
pip install -r requirements.txt
```
This downloads `python-telegram-bot`, `google-generativeai`, `chromadb`, `pymupdf`,
and `python-dotenv`. It can take a couple of minutes.

> **If you see an error mentioning `chroma-hnswlib`, `Microsoft Visual C++ 14.0`, or
> "building wheel ... failed"** — you're almost certainly on Python 3.13/3.14. Delete
> the `.venv` folder, install Python 3.11 (Section 1.1), and redo Step 4 with
> `py -3.11` / `python3.11`.

---

## 5. Configure your keys (the `.env` file)

The project ships with a template called `.env.example`. You make a real copy named
`.env` and put your keys in it.

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
notepad .env
```

**macOS / Linux:**
```bash
cp .env.example .env
nano .env     # or: open -e .env   (macOS)
```

Edit the file so it looks like this, with **your** real values:
```
TELEGRAM_BOT_TOKEN=8123456789:AAH....your-token....xyz
GEMINI_API_KEY=your-gemini-key
```
Save and close.

> ⚠️ **Common mistake:** put the keys in **`.env`**, NOT in `.env.example`. The
> program only reads `.env`. (`.env` is also git-ignored, so your secrets won't be
> committed.)

---

## 6. Run the bot

With the venv still active and `.env` filled in:
```bash
python main.py
```
You should see logging that ends with something like:
```
... | INFO | __main__ | Starting Telegram PDF RAG bot…
... | INFO | telegram.ext.Application | Application started
```
That means it's **running and listening**. Leave this terminal open — closing it
stops the bot.

---

## 7. Verify it works

1. Open Telegram and go to your bot (`https://t.me/<your_bot_username>` or search its
   username).
2. Send **`/start`** → you should get a welcome message.
3. **Upload a PDF**: tap the 📎 attach icon → File → pick a text-based PDF (under
   20 MB). The bot replies "Processing…" then "✅ Done … indexed into N chunks."
4. **Ask a question** about the PDF (just type it, or use `/ask your question`). You
   get an answer drawn only from your document.
5. Ask something **not** in the PDF → the bot says *"I couldn't find that information
   in your uploaded documents."* (it won't make things up).
6. Try the commands: `/list`, `/clear_memory`, `/clear`.

If all of that works, you're done. 🎉

---

## 8. Everyday use (starting and stopping)

**To start the bot again later:**
```bash
# 1. open a terminal in the telegram_pdf_rag folder, then activate the venv:
# Windows:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 2. run it:
python main.py
```

**To stop the bot:** click the terminal and press **Ctrl + C**.

You do **not** reinstall dependencies each time — only the first time (Step 4.2) or
after the code's requirements change.

---

## 9. Troubleshooting

**`pip install` fails with `chroma-hnswlib` / `Microsoft Visual C++ 14.0 is required` /
"failed building wheel"**
→ You're on Python 3.13/3.14. Use **Python 3.11**. Delete `.venv`, recreate it with
`py -3.11`/`python3.11`, and `pip install -r requirements.txt` again.

**(Windows) `Activate.ps1 ... running scripts is disabled on this system`**
→ Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same
PowerShell window, then run the activate command again.

**`python` / `py` / `pip` "not found"**
→ Reopen the terminal (PATH updates only apply to new windows). On macOS/Linux use
`python3.11`/`pip3`. On Windows make sure you ticked "Add to PATH" during install.

**Bot starts but a startup error says `Missing required environment variable(s)`**
→ Your keys aren't being read. Make sure the file is named exactly **`.env`** (not
`.env.txt` or `.env.example`) and is in the `telegram_pdf_rag` folder, with both
`TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` filled in.

**Bot runs but doesn't reply in Telegram**
→ Check: (a) the `python main.py` terminal is still open and shows no errors;
(b) you're messaging the *correct* bot (the username BotFather gave you); (c) the
token in `.env` matches that bot. If you regenerated the token, update `.env`.

**Upload works, but every question says "I couldn't find that information…"**
→ Usually fine for questions truly not in the PDF. If it happens for everything,
confirm the PDF is **text-based**, not scanned images (this bot has no OCR).

**Error in the terminal: `404 ... model ... is not found` (Gemini)**
→ Your key's endpoint doesn't support the configured model. This project is already
set to `gemini-2.5-flash` and `gemini-embedding-001` (in `config.py`). If you changed
those to older names like `gemini-1.5-flash`, change them back.

**Error in the terminal: `429 ... quota` (Gemini)**
→ You hit the free-tier limit. See [Section 10](#10-notes-models-and-free-tier-limits).
Wait for the reset, or use a paid key.

---

## 10. Notes: models and free-tier limits

- **Models used:** `gemini-2.5-flash` (answers) and `gemini-embedding-001`
  (search indexing), configured in `config.py`. These are the names that work with
  current Google AI Studio keys.
- **Free-tier limits (the main thing to know):**
  - **Answers** are capped at roughly **20 requests per day** on the free tier. After
    that, questions error until the daily reset.
  - **Indexing (embeddings)** is limited to about **100 requests per minute**, so a
    very large PDF indexes slowly (the bot waits out the limit and continues).
  - **Daily limits reset at midnight US Pacific time.**
  - For heavier use, use a **paid Gemini API key**, or switch `GEMINI_MODEL` in
    `config.py` to a model with a higher free daily limit (e.g. `gemini-2.0-flash`).
- **Your data is local:** uploaded-document vectors live in a `chroma_db/` folder next
  to the code; conversation memory is in RAM and resets when you stop the bot.
- **Never commit `.env`** — it holds your secrets and is already git-ignored.
