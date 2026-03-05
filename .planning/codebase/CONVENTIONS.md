# Coding Conventions

**Analysis Date:** 2026-03-05

## Naming Patterns

**Files:**
- Single-file project: `main.py` holds all application logic (bot handlers, business logic, entry point)
- Flat structure: no submodules or packages

**Constants:**
- SCREAMING_SNAKE_CASE for all module-level constants
- Examples: `DEFAULT_DELTA`, `DEFAULT_INTERVAL_SEC`, `PRICE_HISTORY_MAX`, `SET_DELAY`, `SET_DELTA`
- Config key constants prefixed with `CFG_`: `CFG_TASK`, `CFG_DELTA`, `CFG_INTERVAL`, `CFG_LAST_PRICE`, `CFG_LAST_AT`
- State key constants prefixed with `AWAITING`: `AWAITING`, `AWAITING_DELAY`, `AWAITING_DELTA`

**Functions:**
- snake_case for all functions
- Command handlers named after command: `start`, `stop`, `hello`, `menu`, `status`
- Event handlers prefixed with `on_`: `on_menu_button`, `on_text_input`, `on_error`
- Async helpers: descriptive verb phrases: `send_price_loop`, `analyze_price`

**Variables:**
- snake_case throughout
- Descriptive names: `price_history`, `interval_sec`, `last_price`, `last_at`
- Type annotations used on function parameters and return values

**Types:**
- `Optional[T]` from `typing` for nullable values (e.g., `Optional[float]`, `Optional[asyncio.Task]`)
- `list[float]` modern generic syntax used in function signatures

## Code Style

**Formatting:**
- No formatter config detected (no `.prettierrc`, `pyproject.toml`, or `.flake8`)
- Consistent 4-space indentation throughout
- Single blank lines between logical sections within functions
- Two blank lines between top-level definitions (PEP 8 style)

**Linting:**
- No linter config detected
- Code follows PEP 8 conventions informally

## Import Organization

**Order observed in `main.py`:**
1. Third-party framework imports (`telegram`, `telegram.ext`, `telegram.constants`)
2. Third-party utility imports (`dotenv`, `asyncio`, `websockets`, `json`, `ssl`, `logging`)
3. Standard library typing imports (`from typing import Optional`)

**Style:**
- Specific symbol imports preferred: `from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton`
- Module-level imports only (no local imports inside functions)

## Error Handling

**Patterns:**
- `asyncio.CancelledError` caught explicitly and re-breaks the loop cleanly (graceful shutdown)
- Broad `except Exception as e` used for connection failure recovery in the WebSocket loop
- Nested try/except to swallow send failures while offline (inner `except Exception: pass`)
- User input validation uses `try/except ValueError` with manual `raise ValueError` for range checks
- `on_error` global error handler logs unhandled exceptions via `logger.exception`

**Pattern example — input validation:**
```python
try:
    minutes = int(text)
    if minutes < 0:
        raise ValueError
except ValueError:
    await update.message.reply_text("Please send a whole number of minutes (>= 0).")
    return
```

**Pattern example — reconnection loop:**
```python
except asyncio.CancelledError:
    logger.info("[%s] Price loop cancelled", chat_id)
    break
except Exception as e:
    logger.warning("[%s] Connection failed: %s", chat_id, e)
    await asyncio.sleep(10)
```

## Logging

**Framework:** `logging` (standard library)

**Setup:**
```python
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
```

**Patterns:**
- `logger.info` for lifecycle events (connected, stopped)
- `logger.warning` for recoverable errors (connection failures)
- `logger.exception` for unhandled errors (preserves stack trace via `exc_info`)
- Log messages include `chat_id` as `[%s]` prefix for traceability: `logger.info("[%s] WebSocket connected", chat_id)`
- No structured logging or log levels beyond INFO/WARNING/ERROR

## Comments

**When to Comment:**
- Section headers group related constants: `# Logger`, `# Callback data keys`, `# Defaults`
- Inline comments explain non-obvious decisions: why SSL verification is disabled, timeout rationale
- Warning comments flag dangerous settings: `# ssl check disabled (use with caution)`
- Comments explain "why", not "what", for non-trivial logic

**Docstrings:**
- Used on all non-trivial functions
- Format: single-line or short multi-line, no param/return documentation
- Examples:
  ```python
  def analyze_price(price: float, history: list[float]) -> str:
      """Generate a short price observation from recent history without any API calls."""

  async def send_price_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
      """Maintains a websocket to Binance and sends updates per chat settings.

      Sends at most once per configured interval and only if price differs
      from the last sent by at least configured delta.
      """
  ```
- Simple handlers (e.g., `hello`, `menu`) have no docstrings

## Function Design

**Size:** Functions are small and focused; `send_price_loop` is the largest (~90 lines) because it owns the full WebSocket lifecycle

**Parameters:** Type annotations on all parameters; `context: ContextTypes.DEFAULT_TYPE` and `update: Update` are the standard handler signature

**Return Values:** Handlers return `None`; pure functions return annotated types (`-> str`)

**Async:** All Telegram handlers are `async def`; only `analyze_price` and `main` are synchronous

**Nested functions:** Used sparingly for closures that capture context — `get_delta()` and `get_interval()` defined inside `send_price_loop` to read live settings

## Module Design

**Exports:** No `__all__` defined; single-module application

**Entry Point:**
```python
def main():
    ...

if __name__ == '__main__':
    main()
```

**State Management:**
- Per-chat state stored in `context.chat_data` dict using string constant keys (defined at module level)
- No global mutable state beyond module-level constants and logger
- No classes used; purely procedural/functional style

---

*Convention analysis: 2026-03-05*
