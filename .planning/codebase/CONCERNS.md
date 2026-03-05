# Codebase Concerns

**Analysis Date:** 2026-03-05

## Tech Debt

**Single monolithic file:**
- Issue: All bot logic, handlers, WebSocket loop, and analysis live in one 311-line `main.py`. No separation of concerns.
- Files: `main.py`
- Impact: Adding features or tests requires editing a single growing file; harder to navigate and test in isolation.
- Fix approach: Extract WebSocket/price loop into `price_feed.py`, handlers into `handlers.py`, analysis into `analysis.py`.

**`dotenv` and `python-dotenv` both listed as dependencies:**
- Issue: `requirements.txt` pins both `dotenv==0.9.9` (a different, unrelated package) and `python-dotenv==1.1.1`. The code uses `import dotenv` which resolves to the `dotenv` package, not `python-dotenv`. This creates ambiguity and a potentially wasted or conflicting dependency.
- Files: `requirements.txt`, `main.py` line 4
- Impact: Possible confusion about which env-loading library is authoritative; `dotenv` package may shadow `python-dotenv`'s `load_dotenv` helper.
- Fix approach: Remove `dotenv==0.9.9` from `requirements.txt` and switch the import to `from dotenv import dotenv_values` using `python-dotenv`, or consolidate on one library.

**In-memory state only — no persistence:**
- Issue: All chat settings (`CFG_DELTA`, `CFG_INTERVAL`, `CFG_LAST_PRICE`, `CFG_LAST_AT`) and the running task reference are stored in `context.chat_data`, which is not persisted to disk or any database. A bot restart silently drops all user configuration.
- Files: `main.py` lines 100–164, 185–191
- Impact: Every bot restart resets every user's delay, delta, and last-sent state. Users must reconfigure after any outage.
- Fix approach: Add `PicklePersistence` (built into `python-telegram-bot`) or a lightweight SQLite store to survive restarts.

**Hardcoded Binance stream URL:**
- Issue: The WebSocket URI `wss://fstream.binance.com/ws/btcusdt@aggTrade` is hardcoded on line 92. The trading pair (BTCUSDT) and stream type (aggTrade) are not configurable.
- Files: `main.py` line 92
- Impact: Extending the bot to support other pairs or stream types requires editing source code.
- Fix approach: Extract as a constant or environment variable; accept the symbol as a parameter to `send_price_loop`.

**`price_history` is local to the loop, not stored in chat_data:**
- Issue: `price_history` (line 111) is a local list inside `send_price_loop`. If the loop reconnects due to a WebSocket error, the history is reset. If the task is cancelled and restarted, history is lost.
- Files: `main.py` lines 111, 137–139
- Impact: The `analyze_price` function produces misleading analysis after reconnects because history starts from zero.
- Fix approach: Store `price_history` in `context.chat_data` keyed by a constant, initialized via `setdefault`.

## Known Bugs

**Zero-minute delay sets interval to 0 seconds — effectively unbounded spam:**
- Symptoms: User inputs `0` for delay, which sets `CFG_INTERVAL` to `0`. The interval check `(now - last_at) >= interval_sec` is always true, so the bot sends a message on every aggTrade tick (potentially hundreds per second if `delta` is also small).
- Files: `main.py` lines 249–259
- Trigger: `/menu` → "Set time delay" → input `0`.
- Workaround: Set a nonzero delta via `/menu` to limit sends.

**`menu` command sends to `update.effective_user.id` instead of `update.effective_chat.id`:**
- Symptoms: In group chats, the menu is sent to the user's private DM rather than the group chat where the command was issued. `/start`, `/stop`, `/status` all correctly use `update.effective_chat.id`.
- Files: `main.py` line 220
- Trigger: Issue `/menu` in a group chat.
- Workaround: Use the bot only in private chats.

**`asyncio.CancelledError` re-raised correctly but `wait_for` in `stop()` suppresses all exceptions:**
- Symptoms: `stop()` calls `asyncio.wait_for(task, timeout=2)` inside a bare `except Exception: pass` (line 206–208). If the task raises a non-cancellation exception during teardown, it is silently swallowed.
- Files: `main.py` lines 205–208
- Trigger: Any exception in `send_price_loop` during the 2-second wait after cancellation.
- Workaround: None currently.

## Security Considerations

**SSL certificate verification is disabled:**
- Risk: The WebSocket SSL context explicitly sets `ssl_context.verify_mode = ssl.CERT_NONE` and `check_hostname = False` (lines 97–98). This disables all certificate validation, making the connection vulnerable to man-in-the-middle attacks.
- Files: `main.py` lines 96–98
- Current mitigation: A code comment warns "use with caution."
- Recommendations: Remove these two lines and let the default SSL context validate the Binance certificate. If a proxy is needed in development, use a proper CA bundle rather than disabling verification globally.

**Bot token loaded from `.env` file via `dotenv_values()` — not from environment variables:**
- Risk: `dotenv.dotenv_values(".env")` reads the `.env` file relative to the current working directory. If the process is started from a different directory, the file is not found and `token` is `None`, causing an unhandled crash with no useful error message.
- Files: `main.py` lines 290–291
- Current mitigation: `.gitignore` correctly excludes `.env`.
- Recommendations: Use `os.environ` or `python-dotenv`'s `load_dotenv()` + `os.getenv("TOKEN")` with an explicit error if the value is missing.

**No input sanitization on user-supplied text before sending back to Telegram:**
- Risk: When echoing back the user's configured delta or delay, the values are cast to `float`/`int` first, so injection via those fields is not possible. However, `update.effective_user.first_name` is reflected directly in `/hello` without escaping (line 216) and HTML parse mode is used elsewhere. If a future change uses `first_name` with `ParseMode.HTML`, it would be an XSS-equivalent in Telegram.
- Files: `main.py` line 216
- Current mitigation: `/hello` uses `reply_text` without HTML parse mode, so currently safe.
- Recommendations: Escape user-supplied strings with `html.escape()` as a precaution.

**No authentication — any Telegram user can use the bot:**
- Risk: Any Telegram user who discovers the bot's username can `/start` it and consume Binance WebSocket connections, one per chat. No allowlist or authorization check exists.
- Files: `main.py` lines 180–194
- Current mitigation: None.
- Recommendations: Add an `ALLOWED_CHAT_IDS` environment variable and guard handlers against unauthorized chats.

## Performance Bottlenecks

**One WebSocket connection per chat:**
- Problem: Each `/start` command spawns an independent `send_price_loop` coroutine with its own WebSocket connection to Binance. With N active chats, there are N simultaneous WebSocket connections to the same stream.
- Files: `main.py` lines 86–177, 190
- Cause: No shared feed multiplexer; each loop independently maintains a connection.
- Improvement path: Use a single shared WebSocket feed that fans out to all active chats via `asyncio.Queue` or a pub/sub pattern.

**`price_history.pop(0)` on a plain list is O(n):**
- Problem: The rolling history is maintained by appending to and popping from index 0 of a plain Python list (lines 137–139). For `PRICE_HISTORY_MAX=20` this is negligible, but it is structurally inefficient.
- Files: `main.py` lines 137–139
- Cause: Using `list` instead of `collections.deque(maxlen=20)`.
- Improvement path: Replace `price_history` with `collections.deque(maxlen=PRICE_HISTORY_MAX)`.

**`asyncio.timeout(20)` on every recv causes overhead:**
- Problem: A new `asyncio.timeout` context manager is created for every single WebSocket message received (line 127). On a high-frequency stream like aggTrade, this is called hundreds of times per minute.
- Files: `main.py` line 127
- Cause: Timeout set per-message rather than per-connection or using `websocket.recv()` with a timeout parameter.
- Improvement path: Pass `recv_timeout` at the `websocket.connect()` level or restructure the loop.

## Fragile Areas

**`send_price_loop` reconnects on any exception, including logic errors:**
- Files: `main.py` lines 169–177
- Why fragile: The bare `except Exception` block catches all exceptions, including programming errors (e.g., `AttributeError`, `TypeError`). These will cause an infinite reconnect loop with a 10-second delay rather than surfacing the bug.
- Safe modification: Separate `websockets.exceptions.ConnectionClosed` and network errors from logic errors; let unexpected exceptions propagate to the `on_error` handler.
- Test coverage: No tests exist for this loop.

**`context.chat_data` task reference can hold stale done tasks:**
- Files: `main.py` lines 188–191, 278
- Why fragile: `CFG_TASK` holds a reference to an `asyncio.Task`. Checking `.done()` works, but if the task ends with an unhandled exception, the task object retains the exception silently until `.result()` is called. The `status` handler (line 278) only checks `.done()` and never retrieves or logs task exceptions.
- Safe modification: Add a `task.add_done_callback` on creation to log any task exception immediately.
- Test coverage: None.

## Scaling Limits

**asyncio.Task per chat — no cap:**
- Current capacity: Unlimited active chats, each with one WebSocket connection.
- Limit: Binance may rate-limit or block IPs that open too many simultaneous WebSocket connections. System file descriptor limits also apply.
- Scaling path: Implement a single shared WebSocket feed; add a max-concurrent-chats guard.

## Dependencies at Risk

**`dotenv==0.9.9` (the `dotenv` package, not `python-dotenv`):**
- Risk: The `dotenv` package on PyPI is a separate, minimally-maintained library. It is not the canonical Python dotenv solution. The code's `import dotenv` resolves to this package, which may have different behavior than expected.
- Impact: If the package is abandoned or conflicts arise, env loading breaks.
- Migration plan: Remove `dotenv==0.9.9` from `requirements.txt`, change the import to use `python-dotenv`'s API (`from dotenv import load_dotenv; load_dotenv()`).

**No version pinning for Python itself:**
- Risk: No `.python-version`, `pyproject.toml`, or `runtime.txt` specifies the required Python version. `requirements.txt` was generated against Python 3.11 (`.venv/lib/python3.11`), but nothing enforces this.
- Impact: Running under Python 3.9 would break `list[float]` type hints used inline (lines 49, 111) without `from __future__ import annotations`.
- Migration plan: Add a `.python-version` file (e.g., `3.11`) or a `pyproject.toml` with `requires-python = ">=3.11"`.

## Missing Critical Features

**No tests:**
- Problem: Zero test files exist. No unit tests for `analyze_price`, no integration tests for handlers, no mocking of Telegram or WebSocket APIs.
- Blocks: Safe refactoring, CI pipelines, confidence in correctness of price logic.

**No graceful shutdown on SIGTERM/SIGINT:**
- Problem: When the bot process is killed (e.g., by a systemd restart or container orchestrator), active `send_price_loop` tasks are not explicitly cancelled and awaited. `python-telegram-bot`'s `run_polling()` does handle signals, but any custom tasks stored in `chat_data` are not tracked by the framework and may be abandoned without cleanup.
- Files: `main.py` lines 289–307
- Blocks: Clean deployment restarts in production.

**No rate limiting or flood protection on Telegram sends:**
- Problem: If `delta=0.01` and `interval_sec=0`, the bot will attempt to call `context.bot.send_message` on every aggTrade event. Telegram's Bot API has a flood limit (30 messages/second to different chats, 1 message/second to the same chat). Exceeding it results in `RetryAfter` exceptions that are caught by the generic handler and trigger reconnect loops.
- Files: `main.py` lines 157–164
- Blocks: Reliable operation at aggressive settings.

## Test Coverage Gaps

**`analyze_price` logic is untested:**
- What's not tested: Edge cases — empty history, single-item history, perfectly flat prices, division by zero if `oldest == 0`.
- Files: `main.py` lines 49–83`
- Risk: Incorrect analysis text sent to users without detection.
- Priority: High

**WebSocket reconnection logic is untested:**
- What's not tested: Behavior on connection drop, behavior when `CancelledError` is raised mid-recv, behavior when Binance sends malformed JSON.
- Files: `main.py` lines 113–177
- Risk: Silent infinite loops or missed reconnects in production.
- Priority: High

**Handler input validation is untested:**
- What's not tested: Negative delay edge cases, zero delta rejection, non-numeric input strings.
- Files: `main.py` lines 241–270
- Risk: Regressions in validation logic go undetected.
- Priority: Medium

---

*Concerns audit: 2026-03-05*
