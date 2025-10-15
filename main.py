from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
import dotenv
import asyncio
import websockets
import json
import ssl
import logging
from typing import Optional


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

# Defaults
DEFAULT_DELTA = 2.0  # USD difference required to send
DEFAULT_INTERVAL_SEC = 60  # send at most once every N seconds (1 minute)

DELAY = "Set time delay in minutes"
DELTA = "Set price delta in dollars"

MENU = "<b>Menu</b>\n\nYou are free to choose how often you want to recieve cryptocurrency price updates"
MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(DELAY, callback_data=SET_DELAY)],
    [InlineKeyboardButton(DELTA, callback_data=SET_DELTA)],
])


async def send_price_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Maintains a websocket to Binance and sends updates per chat settings.

    Sends at most once per configured interval and only if price differs
    from the last sent by at least configured delta.
    """
    uri = "wss://fstream.binance.com/ws/btcusdt@aggTrade"

    # SSL: the endpoint is valid; if you are behind a MITM/proxy with self-signed certs,
    # disabling verification avoids CERTIFICATE_VERIFY_FAILED, but is not recommended.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE  # ssl check disabled (use with caution)

    # Helpers to read config live from chat_data so changes apply immediately
    def get_delta() -> float:
        return float(context.chat_data.get(CFG_DELTA, DEFAULT_DELTA))

    def get_interval() -> int:
        return int(context.chat_data.get(CFG_INTERVAL, DEFAULT_INTERVAL_SEC))

    # Last sent trackers in chat_data
    context.chat_data.setdefault(CFG_LAST_PRICE, None)
    context.chat_data.setdefault(CFG_LAST_AT, None)

    while True:
        try:
            # Increase ping timeouts to reduce spurious 1011 ping timeouts on slow networks
            async with websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=30,
                close_timeout=10,
                max_queue=1024,
            ) as websocket:
                logger.info("[%s] WebSocket connected", chat_id)
                while True:
                    # Safety timeout for recv to avoid hanging forever
                    async with asyncio.timeout(20):
                        message = await websocket.recv()

                    # Parse price from aggTrade event
                    price_str = json.loads(message).get("p")
                    if price_str is None:
                        continue
                    price = float(price_str)

                    # Read current settings
                    delta = get_delta()
                    interval_sec = get_interval()

                    # Determine if we should send
                    last_price: Optional[float] = context.chat_data.get(CFG_LAST_PRICE)
                    last_at: Optional[float] = context.chat_data.get(CFG_LAST_AT)
                    now = asyncio.get_running_loop().time()

                    should_send = False
                    # Respect interval (send at most once per interval)
                    if last_at is None or (now - last_at) >= interval_sec:
                        # Only send if delta condition is satisfied
                        if last_price is None or abs(price - last_price) >= delta:
                            should_send = True

                    if should_send:
                        await context.bot.send_message(chat_id, f"BTC/USDT price: {price}")
                        context.chat_data[CFG_LAST_PRICE] = price
                        context.chat_data[CFG_LAST_AT] = now
        except asyncio.CancelledError:
            # Task cancelled from /stop — exit gracefully
            logger.info("[%s] Price loop cancelled", chat_id)
            break
        except Exception as e:
            # On any error, notify once and try to reconnect after a short backoff
            logger.warning("[%s] Connection failed: %s", chat_id, e)
            try:
                await context.bot.send_message(chat_id, "Connection failed. Reconnecting in 10s…")
            except Exception:
                # Ignore send failures while offline
                pass
            await asyncio.sleep(10)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start sending price updates for the current chat."""
    chat_id = update.effective_chat.id

    # Initialize defaults if not present
    context.chat_data.setdefault(CFG_DELTA, DEFAULT_DELTA)
    context.chat_data.setdefault(CFG_INTERVAL, DEFAULT_INTERVAL_SEC)

    task: Optional[asyncio.Task] = context.chat_data.get(CFG_TASK)
    if task is None or task.done():
        task = asyncio.create_task(send_price_loop(context, chat_id))
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
        # Optionally wait a bit for graceful cancellation
        try:
            await asyncio.wait_for(task, timeout=2)
        except Exception:
            pass
        await context.bot.send_message(chat_id, "Stopped sending price updates.")
        logger.info("[%s] Stopped sending price updates.", chat_id)
    else:
        await context.bot.send_message(chat_id, "No active price updates.")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        update.effective_user.id,
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
        await query.message.reply_text("Send delay in minutes (integer >= 0), e.g. 5")
    elif query.data == SET_DELTA:
        context.chat_data[AWAITING] = AWAITING_DELTA
        await query.message.reply_text("Send price delta in USD (number > 0), e.g. 10.5")


async def on_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text replies when bot is awaiting a value from the user."""
    state = context.chat_data.get(AWAITING)
    if not state:
        return  # ignore arbitrary text when not awaiting

    text = (update.message.text or "").strip()

    if state == AWAITING_DELAY:
        try:
            minutes = int(text)
            if minutes < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please send a whole number of minutes (>= 0).")
            return
        context.chat_data[CFG_INTERVAL] = minutes * 60
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
    running = (context.chat_data.get(CFG_TASK) is not None) and (not context.chat_data.get(CFG_TASK).done())
    await context.bot.send_message(
        chat_id,
        f"Current settings:\n- running: {running}\n- delay: {int(interval_sec//60)} min\n- delta: {delta} USD",
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


def main():
    token = dotenv.dotenv_values(".env").get("TOKEN")
    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(CallbackQueryHandler(on_menu_button))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_input))

    # Errors
    app.add_error_handler(on_error)

    app.run_polling()


if __name__ == '__main__':
    main()