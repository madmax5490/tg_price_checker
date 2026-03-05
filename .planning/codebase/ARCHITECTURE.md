# Architecture

**Analysis Date:** 2026-03-05

## Pattern Overview

**Overall:** Single-file monolith with event-driven async architecture

**Key Characteristics:**
- All application logic resides in `main.py` — no module separation
- Telegram Bot API long-polling drives the event loop via `python-telegram-bot`
- Per-chat state managed entirely through `context.chat_data` (in-memory dict)
- One persistent `asyncio.Task` per active chat streams Binance WebSocket price data
- No database, no external state persistence; all state is lost on process restart

## Layers

**Bot Application Layer:**
- Purpose: Registers handlers, builds the Telegram application, starts polling
- Location: `main.py` — `main()` function (lines 289–310)
- Contains: Handler registration, token loading, `app.run_polling()` call
- Depends on: All command/callback handlers defined in the same file
- Used by: Process entrypoint (`if __name__ == '__main__'`)

**Command Handlers:**
- Purpose: Respond to Telegram slash commands sent by users
- Location: `main.py` — `start()`, `stop()`, `hello()`, `menu()`, `status()` functions
- Contains: Chat state reads/writes, task lifecycle management, bot message sends
- Depends on: `context.chat_data` for per-chat config and task storage
- Used by: `CommandHandler` registrations in `main()`

**Interactive Input Handlers:**
- Purpose: Handle inline keyboard button presses and free-text replies for configuration
- Location: `main.py` — `on_menu_button()`, `on_text_input()` functions
- Contains: State machine transitions (`AWAITING` flag in `chat_data`), input validation
- Depends on: `context.chat_data[AWAITING]` to track what input is expected
- Used by: `CallbackQueryHandler`, `MessageHandler` registrations in `main()`

**Price Streaming Layer:**
- Purpose: Connects to Binance Futures WebSocket, filters ticks, sends price alerts
- Location: `main.py` — `send_price_loop()` coroutine (lines 86–177)
- Contains: WebSocket connection loop, reconnect-on-error logic, delta/interval filtering
- Depends on: `context.chat_data` for live config reads, `context.bot.send_message`
- Used by: `start()` which spawns it as an `asyncio.Task`

**Price Analysis Layer:**
- Purpose: Derives a human-readable trend observation from rolling price history
- Location: `main.py` — `analyze_price()` function (lines 49–83)
- Contains: Direction, percentage change, and momentum trend calculation (no external API)
- Depends on: Nothing external; pure function over a list of floats
- Used by: `send_price_loop()` before composing alert messages

## Data Flow

**Price alert flow:**

1. Binance Futures WebSocket (`wss://fstream.binance.com/ws/btcusdt@aggTrade`) streams aggregate trade events
2. `send_price_loop()` receives each message, parses the `"p"` field as a float price
3. Price appended to in-memory `price_history` list (capped at `PRICE_HISTORY_MAX = 20`)
4. Delta and interval checks run against `context.chat_data` values
5. If both checks pass, `analyze_price()` generates a trend string
6. `context.bot.send_message()` delivers formatted HTML message to the chat
7. `CFG_LAST_PRICE` and `CFG_LAST_AT` updated in `chat_data`

**Configuration flow:**

1. User sends `/menu` → bot sends inline keyboard with "Set time delay" and "Set price delta" buttons
2. User taps button → `on_menu_button()` sets `context.chat_data[AWAITING]` to `AWAITING_DELAY` or `AWAITING_DELTA`
3. User types a value → `on_text_input()` reads `AWAITING` state, validates input, writes `CFG_INTERVAL` or `CFG_DELTA` to `chat_data`
4. `send_price_loop()` reads config live on each tick via `get_delta()` / `get_interval()` closures

**State Management:**
- All state stored in `context.chat_data` (dict keyed by constant strings)
- Keys: `CFG_TASK`, `CFG_DELTA`, `CFG_INTERVAL`, `CFG_LAST_PRICE`, `CFG_LAST_AT`, `AWAITING`
- State is per-chat and in-memory; cleared on bot restart
- No database or file persistence

## Key Abstractions

**`send_price_loop` coroutine:**
- Purpose: Encapsulates the full Binance streaming lifecycle for one chat
- Examples: `main.py` lines 86–177
- Pattern: Infinite `while True` loop with inner WebSocket `async with`, reconnects on any exception with 10s backoff and `asyncio.CancelledError` handled for graceful shutdown

**`context.chat_data` as config store:**
- Purpose: Per-chat mutable key-value store provided by `python-telegram-bot`
- Pattern: Constants (`CFG_*`, `AWAITING`) used as keys; defaults set via `setdefault()` at `start()`

**`AWAITING` state machine:**
- Purpose: Tracks whether the bot is waiting for a delay or delta value from the user
- Pattern: Single key in `chat_data` set to `None | AWAITING_DELAY | AWAITING_DELTA`; reset to `None` after successful input

**`analyze_price` pure function:**
- Purpose: Generates trend text from rolling price history without any network calls
- Pattern: Computes direction, percent change, and half-window momentum comparison

## Entry Points

**Process start:**
- Location: `main.py` lines 310–311 (`if __name__ == '__main__': main()`)
- Triggers: Direct Python execution (`python main.py`)
- Responsibilities: Loads token from `.env`, builds Telegram `Application`, registers all handlers, starts polling loop

**`/start` command:**
- Location: `main.py` `start()` function
- Triggers: User sends `/start` in Telegram chat
- Responsibilities: Initializes `chat_data` defaults, creates `asyncio.Task` for `send_price_loop`

**`/stop` command:**
- Location: `main.py` `stop()` function
- Triggers: User sends `/stop` in Telegram chat
- Responsibilities: Cancels the running `asyncio.Task`, waits up to 2s for graceful exit

## Error Handling

**Strategy:** Log-and-reconnect for WebSocket errors; global error handler for unhandled bot errors

**Patterns:**
- `send_price_loop` catches all exceptions except `CancelledError`, logs a warning, notifies the chat, sleeps 10s, then reconnects
- `asyncio.CancelledError` is caught explicitly and causes clean loop exit
- `asyncio.timeout(20)` wraps each `websocket.recv()` to prevent indefinite hangs
- `on_error()` is registered as a global error handler; logs via `logger.exception()`
- Notification send failures inside the reconnect path are silently swallowed

## Cross-Cutting Concerns

**Logging:** Python `logging` module; `basicConfig(level=logging.INFO)`; logger named `__name__`; log lines include `chat_id` for context

**Validation:** Input validation done inline in `on_text_input()`; invalid values return an error message and do not update state

**Authentication:** No user authentication; any Telegram user who messages the bot can control it

---

*Architecture analysis: 2026-03-05*
