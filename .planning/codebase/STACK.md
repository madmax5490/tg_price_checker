# Technology Stack

**Analysis Date:** 2026-03-05

## Languages

**Primary:**
- Python 3.11.9 - All application code (`main.py`)

## Runtime

**Environment:**
- CPython 3.11.9 (via system install at `/Library/Frameworks/Python.framework/Versions/3.11/`)

**Package Manager:**
- pip 24.0
- Virtual environment: `.venv/` (Python venv)
- Lockfile: `requirements.txt` present with pinned versions

## Frameworks

**Core:**
- `python-telegram-bot` 22.5 - Telegram Bot API wrapper; provides `ApplicationBuilder`, `CommandHandler`, `CallbackQueryHandler`, `MessageHandler`, `ContextTypes`

**Build/Dev:**
- None detected (no build tooling, linters, or formatters configured)

## Key Dependencies

**Critical:**
- `python-telegram-bot==22.5` - Core bot framework; handles polling, handlers, chat_data state
- `websockets==15.0.1` - WebSocket client for real-time Binance price stream (`wss://fstream.binance.com/ws/btcusdt@aggTrade`)
- `python-dotenv==1.1.0` / `dotenv==0.9.9` - Loads `TOKEN` from `.env` file at startup
- `httpx==0.28.1` - HTTP client (transitive dependency of python-telegram-bot)
- `anyio==4.11.0` - Async I/O abstraction (transitive)

**Infrastructure:**
- `asyncio` (stdlib) - All async operations; task management for per-chat price loops
- `ssl` (stdlib) - SSL context for WebSocket connection (hostname verification disabled)
- `json` (stdlib) - Parsing Binance WebSocket trade messages
- `logging` (stdlib) - Application-level logging via `logging.basicConfig(level=logging.INFO)`

## Configuration

**Environment:**
- Configured via `.env` file in project root (read by `dotenv.dotenv_values(".env")` in `main()`)
- `.env` is gitignored; `.env.example` provided as template
- Required variable: `TOKEN` — Telegram Bot API token

**Build:**
- No build config files present
- No `pyproject.toml`, `setup.py`, or `setup.cfg`

## Platform Requirements

**Development:**
- Python 3.11+
- Virtual environment setup: `python3 -m venv .venv && pip install -r requirements.txt`
- `.env` file with valid `TOKEN` value

**Production:**
- Any Python 3.11+ environment (Linux/macOS/Windows)
- Long-running process via `app.run_polling()` (polling mode, no webhook server required)
- No external infrastructure dependencies (no database, no message queue, no web server)

---

*Stack analysis: 2026-03-05*
