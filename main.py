import asyncio
import html
import json
import logging
import os
import ssl
from collections import deque
from typing import Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    PicklePersistence,
    filters,
)
import websockets

# Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Callback data keys
SET_DELAY = "SET_DELAY"
SET_DELTA = "SET_DELTA"

# Chat state keys
AWAITING = "awaiting_input"
AWAITING_DELAY = "awaiting_delay"
AWAITING_DELTA = "awaiting_delta"

# Chat config keys
CFG_TASK = "price_task"
CFG_DELTA = "delta"
CFG_INTERVAL = "interval_sec"
CFG_LAST_PRICE = "last_sent_price"
CFG_LAST_AT = "last_sent_at"
CFG_HISTORY = "price_history"

# Defaults
DEFAULT_DELTA = 2.0          # USD difference required to send
DEFAULT_INTERVAL_SEC = 60    # send at most once every N seconds
MIN_INTERVAL_SEC = 30        # floor to prevent spam (0.5 minutes)

DELAY = "Set time delay in minutes"
DELTA = "Set price delta in dollars"

PRICE_HISTORY_MAX = 20  # rolling ticks kept for analysis

BINANCE_URI = "wss://fstream.binance.com/ws/btcusdt@aggTrade"

MENU = "<b>Menu</b>\n\nYou are free to choose how often you want to recieve cryptocurrency price updates"
MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(DELAY, callback_data=SET_DELAY)],
    [InlineKeyboardButton(DELTA, callback_data=SET_DELTA)],
])

# ---------------------------------------------------------------------------
# Shared WebSocket feed — one connection for all chats
# ---------------------------------------------------------------------------
_subscribers: dict[int, asyncio.Queue] = {}
_feed_task: Optional[asyncio.Task] = None


def _make_ssl_context() -> ssl.SSLContext:
    """Build SSL context, respecting SSL_CA_BUNDLE and SSL_VERIFY env vars."""
    ca_bundle = os.getenv("SSL_CA_BUNDLE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    if os.getenv("SSL_VERIFY", "").lower() == "false":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.warning("SSL verification disabled via SSL_VERIFY=false")
        return ctx
    return ssl.create_default_context()


async def price_feed() -> None:
    """Single shared WebSocket that fans out prices to all per-chat queues."""
    ssl_context = _make_ssl_context()
    while True:
        try:
            async with websockets.connect(
                BINANCE_URI,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=30,
                close_timeout=10,
                max_queue=1024,
            ) as websocket:
                logger.info("Shared price feed connected")
                async for message in websocket:
                    price_str = json.loads(message).get("p")
                    if price_str is None:
                        continue
                    price = float(price_str)
                    for queue in list(_subscribers.values()):
                        try:
                            queue.put_nowait(price)
                        except asyncio.QueueFull:
                            pass  # slow consumer — skip tick
        except asyncio.CancelledError:
            logger.info("Price feed cancelled")
            break
        except Exception as e:
            logger.warning("Price feed connection failed: %s", e)
            await asyncio.sleep(10)


async def _start_feed(app) -> None:
    global _feed_task
    _feed_task = asyncio.create_task(price_feed())


async def _stop_feed(app) -> None:
    global _feed_task
    if _feed_task and not _feed_task.done():
        _feed_task.cancel()
        try:
            await _feed_task
        except (asyncio.CancelledError, Exception):
            pass


# ---------------------------------------------------------------------------
# Price analysis
# ---------------------------------------------------------------------------

def analyze_price(price: float, history: list[float]) -> str:
    """Generate a short price observation from recent history."""
    if len(history) < 2:
        return ""

    oldest = history[0]
    if oldest == 0:
        return ""

    change = price - oldest
    pct = (change / oldest) * 100

    if len(history) >= 3:
        mid = history[len(history) // 2]
        first_half_change = mid - oldest
        second_half_change = price - mid
        if first_half_change * second_half_change < 0:
            trend = "reversing"
        elif abs(second_half_change) > abs(first_half_change) * 1.5:
            trend = "accelerating"
        else:
            trend = "steady"
    else:
        trend = "steady"

    direction = "up" if change >= 0 else "down"
    abs_pct = abs(pct)

    if abs_pct < 0.1:
        strength = "virtually flat"
    elif abs_pct < 0.3:
        strength = f"slightly {direction}"
    elif abs_pct < 1.0:
        strength = f"moderately {direction}"
    else:
        strength = f"sharply {direction}"

    return f"{strength.capitalize()} {abs(change):,.1f} USD ({abs_pct:.2f}%) over last {len(history)} ticks, trend {trend}."


# ---------------------------------------------------------------------------
# Per-chat price loop (reads from shared feed queue)
# ---------------------------------------------------------------------------

async def chat_price_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Reads from the shared feed and sends updates based on per-chat settings."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _subscribers[chat_id] = queue

    # Persist history across restarts via chat_data
    price_history: deque[float] = context.chat_data.setdefault(
        CFG_HISTORY, deque(maxlen=PRICE_HISTORY_MAX)
    )
    context.chat_data.setdefault(CFG_LAST_PRICE, None)
    context.chat_data.setdefault(CFG_LAST_AT, None)

    try:
        while True:
            price = await queue.get()
            price_history.append(price)

            delta = float(context.chat_data.get(CFG_DELTA, DEFAULT_DELTA))
            interval_sec = int(context.chat_data.get(CFG_INTERVAL, DEFAULT_INTERVAL_SEC))

            last_price: Optional[float] = context.chat_data.get(CFG_LAST_PRICE)
            last_at: Optional[float] = context.chat_data.get(CFG_LAST_AT)
            now = asyncio.get_running_loop().time()

            should_send = False
            if last_at is None or (now - last_at) >= interval_sec:
                if last_price is None or abs(price - last_price) >= delta:
                    should_send = True

            if should_send:
                analysis = analyze_price(price, list(price_history))
                text = f"BTC/USDT: <b>${price:,.2f}</b>"
                if analysis:
                    text += f"\n{analysis}"
                await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
                context.chat_data[CFG_LAST_PRICE] = price
                context.chat_data[CFG_LAST_AT] = now
    except asyncio.CancelledError:
        logger.info("[%s] Chat price loop cancelled", chat_id)
    finally:
        _subscribers.pop(chat_id, None)


def _log_task_exception(task: asyncio.Task, chat_id: int) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error("[%s] Price loop exited with error", chat_id, exc_info=exc)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start sending price updates for the current chat."""
    chat_id = update.effective_chat.id
    context.chat_data.setdefault(CFG_DELTA, DEFAULT_DELTA)
    context.chat_data.setdefault(CFG_INTERVAL, DEFAULT_INTERVAL_SEC)

    task: Optional[asyncio.Task] = context.chat_data.get(CFG_TASK)
    if task is None or task.done():
        task = asyncio.create_task(chat_price_loop(context, chat_id))
        task.add_done_callback(lambda t: _log_task_exception(t, chat_id))
        context.chat_data[CFG_TASK] = task
        await context.bot.send_message(chat_id, "Started sending price updates.")
    else:
        await context.bot.send_message(chat_id, "Price updates are already running.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop sending price updates for the current chat."""
    chat_id = update.effective_chat.id
    task: Optional[asyncio.Task] = context.chat_data.get(CFG_TASK)

    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        await context.bot.send_message(chat_id, "Stopped sending price updates.")
        logger.info("[%s] Stopped sending price updates.", chat_id)
    else:
        await context.bot.send_message(chat_id, "No active price updates.")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = html.escape(update.effective_user.first_name)
    await update.message.reply_text(f"Hello {name}")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        update.effective_chat.id,  # Fixed: was effective_user.id (broke group chats)
        MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=MENU_MARKUP,
    )


async def on_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline menu button taps for setting delay/delta."""
    query = update.callback_query
    await query.answer()

    if query.data == SET_DELAY:
        context.chat_data[AWAITING] = AWAITING_DELAY
        await query.message.reply_text("Send delay in minutes (integer >= 1), e.g. 5")
    elif query.data == SET_DELTA:
        context.chat_data[AWAITING] = AWAITING_DELTA
        await query.message.reply_text("Send price delta in USD (number > 0), e.g. 10.5")


async def on_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text replies when bot is awaiting a value from the user."""
    state = context.chat_data.get(AWAITING)
    if not state:
        return

    text = (update.message.text or "").strip()

    if state == AWAITING_DELAY:
        try:
            minutes = int(text)
            if minutes < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please send a whole number of minutes (>= 1).")
            return
        context.chat_data[CFG_INTERVAL] = max(minutes * 60, MIN_INTERVAL_SEC)
        context.chat_data[AWAITING] = None
        await update.message.reply_text(f"Delay set to {minutes} minute(s).")
    elif state == AWAITING_DELTA:
        try:
            delta = float(text)
            if delta <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please send a positive number for delta, e.g. 2 or 10.5.")
            return
        context.chat_data[CFG_DELTA] = delta
        context.chat_data[AWAITING] = None
        await update.message.reply_text(f"Delta set to {delta} USD.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current settings for this chat."""
    chat_id = update.effective_chat.id
    delta = context.chat_data.get(CFG_DELTA, DEFAULT_DELTA)
    interval_sec = context.chat_data.get(CFG_INTERVAL, DEFAULT_INTERVAL_SEC)
    task = context.chat_data.get(CFG_TASK)
    running = task is not None and not task.done()
    await context.bot.send_message(
        chat_id,
        f"Current settings:\n- running: {running}\n- delay: {int(interval_sec // 60)} min\n- delta: {delta} USD",
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN missing: set TOKEN in .env or as an environment variable")

    persistence = PicklePersistence(filepath="bot_data.pkl")
    app = (
        ApplicationBuilder()
        .token(token)
        .persistence(persistence)
        .post_init(_start_feed)
        .post_shutdown(_stop_feed)
        .build()
    )

    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(CallbackQueryHandler(on_menu_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_input))

    app.add_error_handler(on_error)

    app.run_polling()


if __name__ == '__main__':
    main()
