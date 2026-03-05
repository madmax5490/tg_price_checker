# Codebase Structure

**Analysis Date:** 2026-03-05

## Directory Layout

```
tg_price_checker/
├── main.py             # Entire application — bot, handlers, price loop, analysis
├── requirements.txt    # Pinned Python dependencies
├── .env.example        # Environment variable template (safe to commit)
├── .env                # Actual secrets — never committed (in .gitignore)
├── .gitignore          # Ignores .env, .env.*, .venv/
├── .venv/              # Local Python virtual environment (not committed)
├── .planning/          # GSD planning documents
│   └── codebase/       # Codebase analysis docs (this file lives here)
└── .idea/              # JetBrains IDE project files
```

## Directory Purposes

**.planning/codebase/:**
- Purpose: GSD codebase mapping documents consumed by `/gsd:plan-phase` and `/gsd:execute-phase`
- Contains: ARCHITECTURE.md, STRUCTURE.md, and other analysis docs
- Generated: By GSD `map-codebase` command
- Committed: Yes

**.venv/:**
- Purpose: Isolated Python 3.11 virtual environment
- Contains: Installed packages (pip, python-telegram-bot, websockets, etc.)
- Generated: Via `python -m venv .venv` and `pip install -r requirements.txt`
- Committed: No (in .gitignore)

**.idea/:**
- Purpose: JetBrains IDE (PyCharm) project configuration
- Contains: Run configurations, inspection profiles, VCS settings
- Committed: Yes (partially — `.idea/.gitignore` scopes what is tracked)

## Key File Locations

**Entry Point:**
- `main.py`: Single file containing all application code — bot setup, all Telegram handlers, Binance WebSocket streaming loop, price analysis logic

**Configuration:**
- `.env`: Runtime secrets (`TOKEN=...`) — loaded by `dotenv.dotenv_values(".env")` in `main()`, must exist in working directory at runtime
- `.env.example`: Template showing required keys, safe to commit
- `requirements.txt`: All Python dependencies with pinned versions

**Core Logic:**
- `main.py` — `send_price_loop()`: Binance streaming and alert throttling (lines 86–177)
- `main.py` — `analyze_price()`: Trend analysis pure function (lines 49–83)
- `main.py` — `main()`: Application bootstrap and handler registration (lines 289–310)

## Naming Conventions

**Files:**
- Snake_case Python modules: `main.py`
- Uppercase with extension for requirements: `requirements.txt`
- Dotfiles for config: `.env`, `.env.example`, `.gitignore`

**Functions:**
- Snake_case for all functions: `send_price_loop`, `analyze_price`, `on_menu_button`, `on_text_input`
- Telegram command handlers named after the command: `start`, `stop`, `hello`, `menu`, `status`
- Event handlers prefixed with `on_`: `on_menu_button`, `on_text_input`, `on_error`

**Constants:**
- SCREAMING_SNAKE_CASE for all module-level constants: `SET_DELAY`, `CFG_TASK`, `DEFAULT_DELTA`, `PRICE_HISTORY_MAX`
- `CFG_` prefix for chat_data config keys: `CFG_TASK`, `CFG_DELTA`, `CFG_INTERVAL`, `CFG_LAST_PRICE`, `CFG_LAST_AT`
- `AWAITING_` prefix for input-state values: `AWAITING_DELAY`, `AWAITING_DELTA`

## Where to Add New Code

**New Telegram command:**
- Implementation: Add handler function to `main.py` following the signature `async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`
- Registration: Add `app.add_handler(CommandHandler("name", name))` in `main()` in `main.py`

**New chat_data config key:**
- Define a `CFG_` constant at the top of `main.py` alongside existing constants
- Initialize with `context.chat_data.setdefault(CFG_NEW_KEY, DEFAULT_VALUE)` in `start()`
- Read live inside `send_price_loop()` via a closure if it applies to the streaming loop

**New menu option:**
- Add a callback data constant (e.g., `SET_FOO = "SET_FOO"`) in `main.py`
- Add an `InlineKeyboardButton` row to `MENU_MARKUP`
- Handle the new `query.data` case in `on_menu_button()`
- Add a matching `elif state == AWAITING_FOO:` branch in `on_text_input()`

**Utilities / shared helpers:**
- Currently no separate module exists; add a new file (e.g., `utils.py`) at the project root and import into `main.py` if the file grows

**New feature module:**
- Place new `.py` files at the project root (no `src/` subdirectory convention exists yet)
- Import into `main.py`; the project has no package structure

## Special Directories

**.planning/:**
- Purpose: GSD workflow documents (phases, codebase maps)
- Generated: By GSD commands
- Committed: Yes

**.venv/:**
- Purpose: Python virtual environment
- Generated: Developer-created locally
- Committed: No

---

*Structure analysis: 2026-03-05*
